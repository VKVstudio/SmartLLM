"""Lock-aware GPU state machine, memory guard, and process cleanup (Opus Spec Q6)."""

from __future__ import annotations

import atexit
from enum import Enum
import os
from pathlib import Path
import signal
import subprocess
from typing import Any

from ..os_compat import CrossPlatformFileLock, get_system_telemetry, is_linux, is_windows


class GPUState(str, Enum):
    IDLE = "idle"
    LLM_LOADING = "llm_loading"
    LLM_READY = "llm_ready"
    SWITCHING = "switching"
    IMAGE_RUNNING = "image_running"
    ERROR = "error"


class MemoryGuardError(RuntimeError):
    """Raised when MemAvailable < model_host_bytes + 3 GiB."""


class GPULockBusyError(RuntimeError):
    """Raised when gpu.lock is held by another process."""


def inspect_lock_holder_non_destructive(lock_path: Path) -> str | None:
    """Check if lock_path is held without writing to or modifying the file."""
    if not lock_path.exists():
        return None
    if is_linux() and Path("/proc/locks").exists():
        try:
            inode = lock_path.stat().st_ino
            for line in Path("/proc/locks").read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) >= 6 and parts[1] == "FLOCK":
                    dev_ino = parts[5].split(":")
                    if len(dev_ino) == 3 and int(dev_ino[2]) == inode:
                        pid = int(parts[4])
                        if pid != os.getpid():
                            comm_p = Path(f"/proc/{pid}/comm")
                            comm = comm_p.read_text(encoding="utf-8").strip() if comm_p.exists() else "process"
                            return f"{comm} (pid {pid})"
        except Exception:
            pass
    return None


class GPUEngineController:
    """Sequential GPU state machine (idle -> llm_loading -> llm_ready <-> switching <-> image_running)."""

    def __init__(
        self,
        lock_path: Path,
        allow_lock_write: bool = False,
        default_model_host_gib: float = 0.0,
    ) -> None:
        self.lock_path = lock_path
        self.allow_lock_write = allow_lock_write
        self.default_model_host_gib = default_model_host_gib
        self.state: GPUState = GPUState.IDLE
        self.last_error: str | None = None
        self.tok_per_sec: float = 0.0
        self._lock = CrossPlatformFileLock(lock_path) if allow_lock_write else None
        self._children: list[subprocess.Popen[Any]] = []
        atexit.register(self.cleanup_children)

    def check_lock_owner(self) -> str | None:
        if self.allow_lock_write and self._lock is not None and self._lock._fh is not None:
            return "self"
        holder = inspect_lock_holder_non_destructive(self.lock_path)
        if holder:
            return holder
        if self.allow_lock_write and self._lock is not None:
            if not self._lock.acquire():
                return "external_lock_holder"
            self._lock.release()
        return None

    def check_memory_guard(self, model_host_bytes: int | None = None) -> dict[str, Any]:
        """Enforce MemAvailable >= model_host_bytes + 3 GiB (Q6)."""
        tel = get_system_telemetry()
        avail_bytes = int(float(tel["mem_avail_gib"]) * (1024**3))
        req_host = model_host_bytes if model_host_bytes is not None else int(self.default_model_host_gib * (1024**3))
        min_required = req_host + 3 * (1024**3)
        if avail_bytes < min_required:
            req_gib = round(min_required / (1024**3), 2)
            raise MemoryGuardError(
                f"Memory guard refused load: MemAvailable ({tel['mem_avail_gib']} GiB) < required ({req_gib} GiB = model + 3.0 GiB margin)"
            )
        return {"passed": True, "mem_avail_gib": tel["mem_avail_gib"], "required_gib": round(min_required / (1024**3), 2)}

    def acquire_or_raise(self, model_host_bytes: int | None = None) -> None:
        holder = self.check_lock_owner()
        if holder:
            raise GPULockBusyError(f"GPU busy: {holder}")
        if self.allow_lock_write and self._lock is not None:
            if not self._lock.acquire():
                raise GPULockBusyError(f"GPU busy: {self.lock_path.name}")
        try:
            self.check_memory_guard(model_host_bytes=model_host_bytes)
        except Exception:
            if self.allow_lock_write and self._lock is not None:
                self._lock.release()
            raise

    def release_lock(self) -> None:
        if self.allow_lock_write and self._lock is not None:
            self._lock.release()

    def transition(self, next_state: GPUState, error: str | None = None) -> GPUState:
        self.state = next_state
        if error is not None:
            self.last_error = error
        elif next_state != GPUState.ERROR:
            self.last_error = None
        return self.state

    def register_child(self, proc: subprocess.Popen[Any]) -> None:
        self._children.append(proc)

    def cleanup_children(self) -> None:
        for proc in list(self._children):
            if proc.poll() is None:
                try:
                    if is_windows():
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False)
                    else:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        self._children.clear()
        if not is_windows():
            try:
                while True:
                    pid, _ = os.waitpid(-1, os.WNOHANG)
                    if pid == 0:
                        break
            except (ChildProcessError, OSError):
                pass

    def status_dict(self) -> dict[str, Any]:
        tel = get_system_telemetry()
        owner = self.check_lock_owner()
        busy = (owner is not None) or (self.state != GPUState.IDLE)
        return {
            "state": self.state.value,
            "gpu_busy": busy,
            "lock_owner": owner or ("self" if busy else "free"),
            "last_error": self.last_error,
            "tok_per_sec": round(self.tok_per_sec, 1),
            "telemetry": tel,
        }
