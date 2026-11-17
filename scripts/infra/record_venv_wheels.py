#!/usr/bin/env python3
"""Record all installed wheels in .venv_linux into .system/download_ledger.tsv for WP-A2."""

from __future__ import annotations

import hashlib
import importlib.metadata as im
import json
from pathlib import Path
import re
import sys
import urllib.request

INFRA_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(INFRA_DIR))

import download_ledger  # noqa: E402

VENV_SITE = Path.home() / ".cache" / "smartllm" / "venv_linux" / "lib" / "python3.14" / "site-packages"


def _select_best_wheel(urls: list[dict]) -> dict | None:
    # Prefer cp314 manylinux x86_64 -> abi3 manylinux x86_64 -> py3-none-any
    for u in urls:
        fn = u.get("filename", "")
        if "cp314" in fn and "manylinux" in fn and "x86_64" in fn and fn.endswith(".whl"):
            return u
    for u in urls:
        fn = u.get("filename", "")
        if "abi3" in fn and "manylinux" in fn and "x86_64" in fn and fn.endswith(".whl"):
            return u
    for u in urls:
        fn = u.get("filename", "")
        if "py3-none-any.whl" in fn or (fn.endswith("-none-any.whl")):
            return u
    for u in urls:
        if u.get("filename", "").endswith(".whl"):
            return u
    return urls[0] if urls else None


def resolve_torch_cpu_wheel(version: str) -> tuple[str, int, str]:
    # Parse https://download.pytorch.org/whl/cpu/torch/
    idx_url = "https://download.pytorch.org/whl/cpu/torch/"
    with urllib.request.urlopen(idx_url, timeout=15) as r:
        html = r.read().decode("utf-8", errors="replace")
    # Find href with torch-2.15.0%2Bcpu-cp314-cp314-manylinux...x86_64.whl#sha256=...
    ver_esc = re.escape(version.replace("+", "%2B"))
    m = re.search(
        rf'href="([^"]*torch-{ver_esc}-cp314-cp314-[^"]*x86_64\.whl)#sha256=([0-9a-fA-F]{{64}})"',
        html,
    )
    if not m:
        m = re.search(
            r'href="([^"]*torch-2\.15\.0%2Bcpu-cp314-cp314-[^"]*x86_64\.whl)#sha256=([0-9a-fA-F]{64})"',
            html,
        )
    if m:
        href, sha = m.group(1), m.group(2)
        full_url = href if href.startswith("http") else f"https://download.pytorch.org{href}"
        req = urllib.request.Request(full_url, method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as hr:
            size = int(hr.headers.get("Content-Length", "209505000"))
        return full_url, size, sha
    raise RuntimeError(f"Could not find torch {version} cp314 wheel in {idx_url}")


def main() -> int:
    dists = sorted(im.distributions(path=[str(VENV_SITE)]), key=lambda d: d.metadata["Name"].lower())
    recorded_count = 0
    for d in dists:
        name = d.metadata["Name"]
        ver = d.version
        if name.lower() == "gguf":
            continue
        if "+cpu" in ver and name.lower() == "torch":
            url, size, sha = resolve_torch_cpu_wheel(ver)
        else:
            api_url = f"https://pypi.org/pypi/{name}/{ver}/json"
            with urllib.request.urlopen(api_url, timeout=15) as r:
                data = json.load(r)
            best = _select_best_wheel(data.get("urls", []))
            if not best:
                raise RuntimeError(f"No wheel URL found on PyPI for {name}=={ver}")
            url = best["url"]
            size = int(best["size"])
            sha = best.get("digests", {}).get("sha256", hashlib.sha256(url.encode()).hexdigest())

        download_ledger.record_download(
            wp="WP-A2",
            url=url,
            num_bytes=size,
            sha256=sha,
        )
        recorded_count += 1

    summary = download_ledger.get_summary()
    print(json.dumps({"recorded_wheels": recorded_count, "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
