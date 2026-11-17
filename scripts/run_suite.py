#!/usr/bin/env python3
"""Entry-point shim for eval/suite/run_suite.py (WP-A1 centralized runner path)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.suite.run_suite import *  # noqa: E402,F401,F403
from eval.suite.run_suite import (  # noqa: E402,F401
    _strip_section_fences,
    assert_local_endpoint,
    check_extraction_completeness,
    clean_model_text,
    extract_files_from_raw,
    main,
    merge_run_summary,
    reextract_task,
    run_task,
)

if __name__ == "__main__":
    main()
