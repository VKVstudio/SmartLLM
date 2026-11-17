#!/usr/bin/env python3
"""Entry-point shim for scripts/step8_run_eval_autonomous.py (WP-A1 centralized Step 8 runner)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.step8_run_eval_autonomous import (  # noqa: E402,F401
    AUDIT_PY,
    BROWSER_LH_MJS,
    DRY_ALLOWED_LENGTH,
    DRY_BASE,
    DRY_MULTIPLIER,
    DRY_PENALTY_LAST_N,
    DRY_SEQUENCE_BREAKERS,
    EOS_LOGIT_BIAS,
    EOS_TOKEN_ID,
    FREQUENCY_PENALTY,
    LOGIT_BIAS_TOKENS,
    MAX_TOKENS,
    MIN_P,
    MODEL_QUEUE,
    PRESENCE_PENALTY,
    REASONING_BUDGET,
    REPEAT_LAST_N,
    REPEAT_PENALTY,
    TEMPERATURE,
    TOP_K,
    TOP_P,
    WATCHDOG_CRIT_AVAIL_MIB,
    WATCHDOG_MAX_CPU_PRIV_WS_GIB,
    WATCHDOG_MAX_PAGEFILE_DELTA_PCT,
    WATCHDOG_MAX_PLE_RSS_KB,
    WATCHDOG_MAX_VRAM_MIB,
    WATCHDOG_MIN_AVAIL_MIB,
    compute_model_stats,
    ensure_clean_vram_and_port,
    evaluate_watchdog_sample,
    load_tasks,
    main,
    run_model_queue_item,
)

if __name__ == "__main__":
    raise SystemExit(main())
