import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

STRATA_CMD = r"C:\Users\user\AppData\Local\Strata\terminal\current\bin\strata.CMD"
DATA_DIR = r"D:\Strata"
PYTHON_EXE = r"D:\projects\SmartLLM\.venv\Scripts\python.exe"
RUN_SUITE_PY = r"D:\projects\SmartLLM\eval\suite\run_suite.py"
TELEMETRY_OUT = r"D:\projects\SmartLLM\research\step3_raw\strata_vram_telemetry.json"


def query_vram() -> dict:
    r1 = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.free,memory.total", "--format=csv,noheader"],
        capture_output=True,
        text=True,
    )
    r2 = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"],
        capture_output=True,
        text=True,
    )
    return {
        "gpu_memory": r1.stdout.strip(),
        "compute_apps": r2.stdout.strip(),
    }


def wait_for_server(port: int = 8080, timeout_sec: int = 120) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1.5)
    return False


def main():
    parser = argparse.ArgumentParser(description="Launch local Strata Gyro-M-64K and run SmartLLM eval/suite")
    parser.add_argument("--max-tokens", type=int, default=24000)
    parser.add_argument("--reasoning-budget", type=int, default=4000)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--tasks", nargs="*", help="Optional subset of task IDs (e.g. t3 t5 t6)")
    args, extra = parser.parse_known_args()
    tasks = (args.tasks or []) + [x for x in extra if not x.startswith("-")]

    print("[1/4] Checking initial GPU VRAM before starting Strata...", flush=True)
    vram_before = query_vram()
    print("VRAM before:", vram_before, flush=True)

    print("[2/4] Launching Strata (Gyro-M-64K, vision=on, port=8080)...", flush=True)
    try:
        launch_res = subprocess.run(
            [
                STRATA_CMD,
                "launch",
                "--preset",
                "Gyro-M-64K",
                "--data-dir",
                DATA_DIR,
                "--vision",
                "on",
                "--no-api-key",
                "--no-tui",
                "--port",
                "8080",
            ],
            capture_output=True,
            text=True,
        )
        print(launch_res.stdout, flush=True)
        if launch_res.returncode != 0:
            print("STDERR:", launch_res.stderr, flush=True)
            sys.exit(launch_res.returncode)

        if not wait_for_server(8080, timeout_sec=60):
            raise RuntimeError("Strata server on 127.0.0.1:8080 did not respond to /v1/models within 60s")

        vram_loaded = query_vram()
        print("[3/4] Strata server online! VRAM loaded:", vram_loaded, flush=True)

        os.makedirs(os.path.dirname(TELEMETRY_OUT), exist_ok=True)
        with open(TELEMETRY_OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(
                {"vram_before": vram_before, "vram_loaded": vram_loaded, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")},
                fh,
                indent=2,
            )

        cmd = [
            PYTHON_EXE,
            "-u",
            RUN_SUITE_PY,
            "--endpoint",
            "http://127.0.0.1:8080/v1/chat/completions",
            "--model-slug",
            "gyro-m-local",
            "--model-id",
            "gyro-m",
            "--reasoning-budget",
            str(args.reasoning_budget),
            "--max-tokens",
            str(args.max_tokens),
        ]
        if args.force:
            cmd.append("--force")
        if tasks:
            cmd.extend(["--tasks"] + tasks)

        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            raise RuntimeError(f"run_suite.py exited with code {proc.returncode}")

    finally:
        print("[4/4] Stopping Strata and freeing GPU VRAM...", flush=True)
        stop_res = subprocess.run(
            [STRATA_CMD, "launch", "--stop", "--data-dir", DATA_DIR],
            capture_output=True,
            text=True,
        )
        print(stop_res.stdout, flush=True)
        vram_after = query_vram()
        if vram_after.get("compute_apps"):
            for line in vram_after["compute_apps"].splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2 and "strata" in parts[1].lower() and parts[0].isdigit():
                    subprocess.run(["taskkill", "/F", "/PID", parts[0]], capture_output=True)
            vram_after = query_vram()
        print("VRAM after stop:", vram_after, flush=True)


if __name__ == "__main__":
    main()
