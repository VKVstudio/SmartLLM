import json
import os
import sys

SUITE_DIR = r"D:\projects\SmartLLM\eval\suite"
RESULTS_DIR = os.path.join(SUITE_DIR, "results")


def aggregate(j1_path: str, j2_path: str, out_path: str) -> dict:
    with open(j1_path, "r", encoding="utf-8") as fh:
        j1 = json.load(fh)
    with open(j2_path, "r", encoding="utf-8") as fh:
        j2 = json.load(fh)

    evals_1 = j1.get("evaluations", {})
    evals_2 = j2.get("evaluations", {})

    models = sorted(set(evals_1.keys()) | set(evals_2.keys()))
    summary = {
        "judge_1_id": j1.get("judge_id", "judge_1"),
        "judge_2_id": j2.get("judge_id", "judge_2"),
        "discrepancy_threshold": 2.0,
        "discrepancies": [],
        "models": {},
    }

    criteria = ("canon", "design", "copy", "ru", "overall")

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
                "judge_2": t2,
                "mean": {},
                "diffs": {},
                "discrepancy_flagged": False,
                "flagged_criteria": [],
            }
            for c in criteria:
                v1 = t1.get(c)
                v2 = t2.get(c)
                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
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

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    print(
        f"Aggregated judge scores -> {out_path} | "
        f"Total discrepancies (>2.0 pts): {len(summary['discrepancies'])}"
    )
    return summary


if __name__ == "__main__":
    p1 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RESULTS_DIR, "judge_1.json")
    p2 = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RESULTS_DIR, "judge_2.json")
    p_out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(RESULTS_DIR, "judges_aggregated.json")
    aggregate(p1, p2, p_out)
