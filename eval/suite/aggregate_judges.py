import argparse
import json
import os
import sys
from pathlib import Path

_ROOT_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from scripts.platform_paths import RESULTS_DIR as _RESULTS_PATH, SUITE_DIR as _SUITE_PATH

SUITE_DIR = str(_SUITE_PATH)
RESULTS_DIR = str(_RESULTS_PATH)

RUBRIC_V3_CRITERIA: tuple[str, ...] = (
    "layout_craft",
    "canon_fidelity",
    "imagery",
    "copy_en",
    "copy_ru",
    "seo_aeo_geo",
    "security",
    "architecture",
    "overall",
)
LEGACY_V1_CRITERIA: tuple[str, ...] = ("canon", "design", "copy", "ru", "overall")


def _extract_judge_family(judge_id: str) -> str:
    jid = (judge_id or "").strip().lower()
    for fam in ("opus", "claude", "carbon", "argon", "gemini", "gpt", "qwen", "human"):
        if fam in jid:
            return fam
    return jid or "unknown"


def _deanonymize_evaluations(raw_evals: dict, blind_map: dict | None) -> dict:
    """Map anonymized pack IDs back to {model_slug: {task_id: scores}} when blind_map is provided."""
    if not blind_map:
        return raw_evals
    pack_map = blind_map.get("packs", blind_map)
    resolved: dict[str, dict[str, dict]] = {}
    for key, val in raw_evals.items():
        if key in pack_map and isinstance(pack_map[key], dict):
            m_slug = str(pack_map[key]["model"])
            t_id = str(pack_map[key]["task"])
            resolved.setdefault(m_slug, {})[t_id] = val
        elif isinstance(val, dict):
            # Already structured as {model_slug: {task_id: scores}}
            resolved.setdefault(key, {}).update(val)
    return resolved


def aggregate(
    j1_path: str,
    j2_path: str | None = None,
    out_path: str | None = None,
    blind_map_path: str | None = None,
) -> dict:
    with open(j1_path, "r", encoding="utf-8") as fh:
        j1 = json.load(fh)

    j2 = None
    if j2_path and os.path.exists(j2_path) and os.path.abspath(j2_path) != os.path.abspath(j1_path):
        with open(j2_path, "r", encoding="utf-8") as fh:
            j2 = json.load(fh)

    blind_map = None
    if blind_map_path and os.path.exists(blind_map_path):
        with open(blind_map_path, "r", encoding="utf-8") as fh:
            blind_map = json.load(fh)

    j1_id = str(j1.get("judge_id", "judge_1"))
    j2_id = str(j2.get("judge_id", "judge_2")) if j2 else None
    fam1 = _extract_judge_family(j1_id)
    fam2 = _extract_judge_family(j2_id) if j2_id else None

    is_dual_independent = bool(j2 is not None and j1_id != j2_id and fam1 != fam2)
    is_blind = bool(
        blind_map is not None
        or (j1.get("blind", False) and (j2 is None or j2.get("blind", False)))
    )
    gate_status = "VERIFIED-BLIND-DUAL-JUDGE" if (is_dual_independent and is_blind) else (
        "DUAL-JUDGE-UNBLINDED" if is_dual_independent else "PENDING-JUDGE"
    )

    evals_1 = _deanonymize_evaluations(j1.get("evaluations", {}), blind_map)
    evals_2 = _deanonymize_evaluations(j2.get("evaluations", {}), blind_map) if j2 else {}

    models = sorted(set(evals_1.keys()) | set(evals_2.keys()))

    # Detect active criteria set (v3 8-criterion + overall vs legacy v1)
    detected_criteria: list[str] = []
    for c in RUBRIC_V3_CRITERIA + LEGACY_V1_CRITERIA:
        if c not in detected_criteria:
            for m in models:
                for t_scores in list(evals_1.get(m, {}).values()) + list(evals_2.get(m, {}).values()):
                    if isinstance(t_scores, dict) and c in t_scores:
                        detected_criteria.append(c)
                        break
    criteria = tuple(detected_criteria) if detected_criteria else RUBRIC_V3_CRITERIA

    summary = {
        "judge_1_id": j1_id,
        "judge_2_id": j2_id,
        "judge_1_family": fam1,
        "judge_2_family": fam2,
        "independent_dual_judge_verified": is_dual_independent,
        "blind_evaluation_verified": is_blind,
        "judge_gate_status": gate_status,
        "criteria": list(criteria),
        "discrepancy_threshold": 2.0,
        "discrepancies": [],
        "models": {},
    }

    for m in models:
        m1 = evals_1.get(m, {})
        m2 = evals_2.get(m, {})
        tasks = sorted(set(m1.keys()) | set(m2.keys()))
        summary["models"][m] = {}

        for t in tasks:
            t1 = m1.get(t, {})
            t2 = m2.get(t, {})
            entry = {
                "judge_1": t1,
                "judge_2": t2 if j2 else None,
                "mean": {},
                "diffs": {},
                "discrepancy_flagged": False,
                "flagged_criteria": [],
                "status": gate_status,
            }
            for c in criteria:
                v1 = t1.get(c) if isinstance(t1, dict) else None
                v2 = t2.get(c) if (j2 and isinstance(t2, dict)) else None
                if j2 is None:
                    entry["mean"][c] = round(float(v1), 2) if isinstance(v1, (int, float)) else None
                    entry["diffs"][c] = None
                elif isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    diff = round(abs(float(v1) - float(v2)), 2)
                    mean_val = round((float(v1) + float(v2)) / 2.0, 2)
                    entry["mean"][c] = mean_val
                    entry["diffs"][c] = diff
                    if diff > 2.0:
                        entry["discrepancy_flagged"] = True
                        entry["flagged_criteria"].append(
                            {"criterion": c, "judge_1": v1, "judge_2": v2, "diff": diff}
                        )
                        summary["discrepancies"].append(
                            {
                                "model": m,
                                "task": t,
                                "criterion": c,
                                "judge_1": v1,
                                "judge_2": v2,
                                "diff": diff,
                            }
                        )
                elif (v1 is None) != (v2 is None):
                    entry["mean"][c] = None
                    entry["diffs"][c] = None
                    entry["discrepancy_flagged"] = True
                    entry["flagged_criteria"].append(
                        {"criterion": c, "judge_1": v1, "judge_2": v2, "diff": "asymmetric_null"}
                    )
                    summary["discrepancies"].append(
                        {
                            "model": m,
                            "task": t,
                            "criterion": c,
                            "judge_1": v1,
                            "judge_2": v2,
                            "diff": "asymmetric_null",
                        }
                    )
                else:
                    entry["mean"][c] = None
                    entry["diffs"][c] = None

            summary["models"][m][t] = entry

    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(summary, fh, indent=2, ensure_ascii=False)
        print(
            f"Aggregated judge scores -> {out_path} | status={gate_status} | "
            f"Total discrepancies (>2.0 pts): {len(summary['discrepancies'])}"
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate blind dual-judge evaluation scores (v3).")
    parser.add_argument("judge_1", nargs="?", default=os.path.join(RESULTS_DIR, "judge_1.json"))
    parser.add_argument("judge_2", nargs="?", default=os.path.join(RESULTS_DIR, "judge_2.json"))
    parser.add_argument("out_path", nargs="?", default=os.path.join(RESULTS_DIR, "judges_aggregated.json"))
    parser.add_argument("--blind-map", default=None, help="Optional JSON mapping anonymized pack IDs to (model, task)")
    args = parser.parse_args()
    aggregate(args.judge_1, args.judge_2, args.out_path, blind_map_path=args.blind_map)


if __name__ == "__main__":
    main()
