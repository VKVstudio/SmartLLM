import argparse
import datetime
import json
import os
import pathlib
import sys
import threading
import time
import urllib.request

ROOT = pathlib.Path(r"D:\projects\SmartLLM")
TARGET_DIR = ROOT / "models" / "Qwen3.8-Flash-Next"
CACHE_DIR = ROOT / "models" / ".hf_cache"
STATUS_FILE = TARGET_DIR / "download_status.json"
MANIFEST_FILE = TARGET_DIR / "official_hf_manifest.json"
LOG_FILE = TARGET_DIR / "download.log"
PID_FILE = TARGET_DIR / "downloader.pid"

(CACHE_DIR / "tmp").mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "xet").mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["HF_HUB_CACHE"] = str(CACHE_DIR)
os.environ["HF_XET_CACHE"] = str(CACHE_DIR / "xet")
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["TMP"] = str(CACHE_DIR / "tmp")
os.environ["TEMP"] = str(CACHE_DIR / "tmp")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
DEFAULT_TOKEN_PATH = pathlib.Path(r"C:\Users\user\.cache\huggingface\token")
if DEFAULT_TOKEN_PATH.exists():
    os.environ["HF_TOKEN_PATH"] = str(DEFAULT_TOKEN_PATH)

from huggingface_hub import hf_hub_download
from safetensors import safe_open

REPO_ID = "Qwen/Qwen3.8-Flash-Next"
API_MANIFEST_URL = f"https://huggingface.co/api/models/{REPO_ID}?blobs=true"


def log_msg(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def fetch_or_load_manifest() -> dict:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    if MANIFEST_FILE.exists() and MANIFEST_FILE.stat().st_size > 1000:
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    req = urllib.request.Request(
        API_MANIFEST_URL, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    MANIFEST_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return data


def build_ordered_file_list(manifest: dict) -> list[dict]:
    siblings = manifest.get("siblings", [])
    by_name = {s["rfilename"]: s for s in siblings}

    # 1. All non-safetensors metadata & tokenizer files
    meta_files = sorted(
        [n for n in by_name if not n.endswith(".safetensors")]
    )

    # 2. Priority 1 shards: Step 5 Pilot (root, visual, layers 0, 1, 2 + PLE dense ends)
    pilot_indices = [1, 2, 3, 4, 5, 37, 57, 58, 59, 130, 131]
    pilot_shards = [
        f"model-{i:05d}-of-00131.safetensors" for i in pilot_indices
    ]

    # 3. Priority 2 shards: Remaining MoE layers & MTP (00038..00056, 00060..00129)
    core_shards = [
        f"model-{i:05d}-of-00131.safetensors"
        for i in range(1, 132)
        if i not in pilot_indices and not (6 <= i <= 36)
    ]

    # 4. Priority 3 shards: Static PLE n-gram lookup shards (00006..00036)
    ple_shards = [
        f"model-{i:05d}-of-00131.safetensors" for i in range(6, 37)
    ]

    ordered_names = meta_files + pilot_shards + core_shards + ple_shards
    return [by_name[name] for name in ordered_names if name in by_name]


def verify_existing_file(fpath: pathlib.Path, expected_size: int) -> bool:
    if not fpath.exists():
        return False
    if fpath.stat().st_size != expected_size:
        return False
    if fpath.name.endswith(".safetensors"):
        try:
            with safe_open(str(fpath), framework="pt", device="cpu") as f:
                keys = f.keys()
                if not keys:
                    return False
        except Exception:
            return False
    return True


def get_incomplete_bytes() -> int:
    dl_cache = TARGET_DIR / ".cache" / "huggingface" / "download"
    if not dl_cache.exists():
        return 0
    total = 0
    for p in dl_cache.glob("*.incomplete"):
        try:
            total += p.stat().st_size
        except OSError:
            pass
    return total


def update_status(
    ordered_files: list[dict],
    current_file: str | None,
    start_time: float,
    session_downloaded_bytes: int,
    state: str = "RUNNING",
):
    total_bytes = sum(f.get("size", 0) for f in ordered_files)
    done_files = 0
    done_shards = 0
    verified_bytes = 0
    for f in ordered_files:
        fname = f["rfilename"]
        fsize = f.get("size", 0)
        fpath = TARGET_DIR / fname
        if fpath.exists() and fpath.stat().st_size == fsize:
            done_files += 1
            verified_bytes += fsize
            if fname.endswith(".safetensors"):
                done_shards += 1

    in_flight_bytes = get_incomplete_bytes()
    effective_bytes = verified_bytes + in_flight_bytes
    elapsed = max(0.001, time.time() - start_time)
    speed_mbps = ((session_downloaded_bytes + in_flight_bytes) / (1024 * 1024)) / elapsed
    remaining_bytes = max(0, total_bytes - effective_bytes)
    eta_hours = (
        (remaining_bytes / (1024 * 1024) / speed_mbps) / 3600.0
        if speed_mbps > 0.1
        else None
    )

    status = {
        "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "pid": os.getpid(),
        "state": state,
        "repo_id": REPO_ID,
        "target_dir": str(TARGET_DIR),
        "files_completed": f"{done_files} / {len(ordered_files)}",
        "shards_completed": f"{done_shards} / 131",
        "current_file": current_file,
        "verified_gb": round(verified_bytes / 1e9, 3),
        "verified_gib": round(verified_bytes / (1024**3), 3),
        "in_flight_mb": round(in_flight_bytes / (1024 * 1024), 1),
        "total_gb": round(total_bytes / 1e9, 3),
        "total_gib": round(total_bytes / (1024**3), 3),
        "percent_complete": round(100.0 * effective_bytes / total_bytes, 2),
        "avg_speed_mib_s": round(speed_mbps, 2),
        "eta_hours": round(eta_hours, 2) if eta_hours is not None else None,
    }
    STATUS_FILE.write_text(
        json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return status


def main():
    parser = argparse.ArgumentParser(
        description="Official Qwen/Qwen3.8-Flash-Next Resumable Downloader"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print current download progress and exit",
    )
    parser.add_argument(
        "--max-shards",
        type=int,
        default=0,
        help="Optional limit on number of shards to download in this run (0 = all 131)",
    )
    args = parser.parse_args()

    manifest = fetch_or_load_manifest()
    ordered_files = build_ordered_file_list(manifest)

    if args.status:
        st = update_status(ordered_files, None, time.time(), 0, state="CHECK")
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return

    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    log_msg(
        f"Starting official download of {REPO_ID} (commit {manifest.get('sha')}, PID={os.getpid()}) -> {TARGET_DIR}"
    )
    start_time = time.time()
    session_bytes = 0
    shards_downloaded_this_run = 0
    current_state = {"file": None, "active": True}

    def _heartbeat():
        while current_state["active"]:
            try:
                if current_state["file"]:
                    update_status(
                        ordered_files,
                        current_state["file"],
                        start_time,
                        session_bytes,
                        state="DOWNLOADING",
                    )
            except Exception:
                pass
            time.sleep(10)

    hb_thread = threading.Thread(target=_heartbeat, daemon=True)
    hb_thread.start()

    for idx, f in enumerate(ordered_files, 1):
        fname = f["rfilename"]
        fsize = f.get("size", 0)
        sha256 = (f.get("lfs") or {}).get("sha256")
        fpath = TARGET_DIR / fname

        if verify_existing_file(fpath, fsize):
            continue

        current_state["file"] = fname
        update_status(
            ordered_files, fname, start_time, session_bytes, state="DOWNLOADING"
        )
        log_msg(
            f"[{idx}/{len(ordered_files)}] Downloading {fname} ({fsize / 1e9:.3f} GB, sha256={str(sha256)[:12]}...)"
        )

        attempt = 0
        while True:
            attempt += 1
            t_file = time.time()
            try:
                hf_hub_download(
                    repo_id=REPO_ID,
                    filename=fname,
                    local_dir=str(TARGET_DIR),
                )
                if not verify_existing_file(fpath, fsize):
                    raise RuntimeError(
                        f"Post-download verification failed for {fname}"
                    )
                dt = max(0.001, time.time() - t_file)
                mbps = (fsize / (1024 * 1024)) / dt
                session_bytes += fsize
                if fname.endswith(".safetensors"):
                    shards_downloaded_this_run += 1
                st = update_status(
                    ordered_files,
                    fname,
                    start_time,
                    session_bytes,
                    state="DOWNLOADING",
                )
                log_msg(
                    f"DONE {fname} in {dt:.1f}s ({mbps:.1f} MiB/s) | Progress: {st['shards_completed']} shards ({st['verified_gb']} / {st['total_gb']} GB, {st['percent_complete']}%)"
                )
                break
            except KeyboardInterrupt:
                log_msg(f"Interrupted by user during {fname}. State saved.")
                update_status(
                    ordered_files,
                    fname,
                    start_time,
                    session_bytes,
                    state="PAUSED",
                )
                sys.exit(130)
            except Exception as e:
                wait_s = min(60, 5 * attempt)
                log_msg(
                    f"WARN attempt {attempt} on {fname}: {e}. Retrying in {wait_s}s..."
                )
                time.sleep(wait_s)
                if attempt >= 50:
                    update_status(
                        ordered_files,
                        fname,
                        start_time,
                        session_bytes,
                        state=f"ERROR: {e}",
                    )
                    raise

        if args.max_shards > 0 and shards_downloaded_this_run >= args.max_shards:
            log_msg(
                f"Reached --max-shards={args.max_shards}. Stopping cleanly."
            )
            update_status(
                ordered_files,
                None,
                start_time,
                session_bytes,
                state="PARTIAL_TARGET_REACHED",
            )
            return

    st = update_status(
        ordered_files, None, start_time, session_bytes, state="COMPLETED"
    )
    log_msg(
        f"ALL 144 FILES (131 SHARDS, {st['verified_gb']} GB) DOWNLOADED AND VERIFIED SUCCESSFULLY!"
    )


if __name__ == "__main__":
    main()
