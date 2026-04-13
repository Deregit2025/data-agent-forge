"""
Regression Suite — Oracle Forge Evaluation Framework

Compares two benchmark result JSON files and reports:
  - Regressions: queries that passed before but fail now
  - Improvements: queries that failed before but pass now
  - Unchanged: queries that are consistently passing or failing
  - Dataset-level pass rate changes

Usage:
    # Compare baseline to a new run
    python -m eval.regression_suite \
        --baseline eval/results/baseline_run.json \
        --current  eval/results/latest.json

    # Compare any two named runs
    python -m eval.regression_suite \
        --baseline eval/results/benchmark_20260410_120000.json \
        --current  eval/results/benchmark_20260411_150000.json

    # Just print a diff without exit code enforcement
    python -m eval.regression_suite --baseline ... --current ... --no_fail
"""

import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass


# ── data helpers ──────────────────────────────────────────────────────────────

def load_result(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Result file not found: {p}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def index_queries(benchmark: dict) -> dict[str, dict]:
    """
    Build a lookup: "dataset/queryN" -> query result dict.
    """
    idx = {}
    for qr in benchmark.get("per_query", []):
        key = f"{qr['dataset']}/query{qr['query_id']}"
        idx[key] = qr
    return idx


# ── diff computation ──────────────────────────────────────────────────────────

@dataclass
class QueryDiff:
    key:            str
    question:       str
    before_pass:    bool
    after_pass:     bool
    before_rate:    float
    after_rate:     float
    delta:          float

    @property
    def is_regression(self) -> bool:
        return self.before_pass and not self.after_pass

    @property
    def is_improvement(self) -> bool:
        return not self.before_pass and self.after_pass

    @property
    def changed(self) -> bool:
        return self.before_pass != self.after_pass


def compute_diff(baseline: dict, current: dict) -> list[QueryDiff]:
    """Compare all queries between two benchmark runs."""
    base_idx = index_queries(baseline)
    curr_idx = index_queries(current)

    all_keys = sorted(set(base_idx) | set(curr_idx))
    diffs = []

    for key in all_keys:
        base_qr = base_idx.get(key)
        curr_qr = curr_idx.get(key)

        if base_qr is None:
            # new query added in current
            diffs.append(QueryDiff(
                key=         key,
                question=    curr_qr["question"],
                before_pass= False,
                after_pass=  curr_qr["majority_pass"],
                before_rate= 0.0,
                after_rate=  curr_qr["pass_rate"],
                delta=       curr_qr["pass_rate"],
            ))
        elif curr_qr is None:
            # query removed in current
            diffs.append(QueryDiff(
                key=         key,
                question=    base_qr["question"],
                before_pass= base_qr["majority_pass"],
                after_pass=  False,
                before_rate= base_qr["pass_rate"],
                after_rate=  0.0,
                delta=       -base_qr["pass_rate"],
            ))
        else:
            diffs.append(QueryDiff(
                key=         key,
                question=    curr_qr["question"],
                before_pass= base_qr["majority_pass"],
                after_pass=  curr_qr["majority_pass"],
                before_rate= base_qr["pass_rate"],
                after_rate=  curr_qr["pass_rate"],
                delta=       round(curr_qr["pass_rate"] - base_qr["pass_rate"], 4),
            ))

    return diffs


def compute_dataset_diff(baseline: dict, current: dict) -> list[dict]:
    """Compare dataset-level pass rates between two runs."""
    base_ds = {d["dataset"]: d for d in baseline.get("per_dataset", [])}
    curr_ds = {d["dataset"]: d for d in current.get("per_dataset", [])}

    all_datasets = sorted(set(base_ds) | set(curr_ds))
    rows = []
    for ds in all_datasets:
        b = base_ds.get(ds, {})
        c = curr_ds.get(ds, {})
        rows.append({
            "dataset":      ds,
            "before_rate":  b.get("pass_rate", 0.0),
            "after_rate":   c.get("pass_rate", 0.0),
            "before_pass":  b.get("pass_count", 0),
            "after_pass":   c.get("pass_count", 0),
            "before_total": b.get("n_queries", 0),
            "after_total":  c.get("n_queries", 0),
            "delta":        round(c.get("pass_rate", 0.0) - b.get("pass_rate", 0.0), 4),
        })
    return rows


# ── report printer ────────────────────────────────────────────────────────────

def print_report(
    baseline: dict,
    current:  dict,
    diffs:    list[QueryDiff],
    ds_diffs: list[dict],
):
    regressions  = [d for d in diffs if d.is_regression]
    improvements = [d for d in diffs if d.is_improvement]
    unchanged    = [d for d in diffs if not d.changed]

    b_rate = baseline.get("pass_rate", 0.0)
    c_rate = current.get("pass_rate",  0.0)
    delta  = round(c_rate - b_rate, 4)
    arrow  = "▲" if delta > 0 else ("▼" if delta < 0 else "→")

    print(f"\n{'='*65}")
    print(f"ORACLE FORGE REGRESSION REPORT")
    print(f"{'='*65}")
    print(f"Baseline: {baseline.get('run_id', '?')}  pass_rate={b_rate*100:.1f}%  ({baseline.get('pass_count',0)}/{baseline.get('total_queries',0)})")
    print(f"Current:  {current.get('run_id',  '?')}  pass_rate={c_rate*100:.1f}%  ({current.get('pass_count',0)}/{current.get('total_queries',0)})")
    print(f"Delta:    {arrow} {abs(delta)*100:.1f}pp")
    print(f"{'='*65}")

    # dataset table
    print(f"\n{'Dataset':<22} {'Before':>7} {'After':>7} {'Delta':>7}")
    print(f"{'-'*45}")
    for row in ds_diffs:
        d_arrow = "▲" if row["delta"] > 0 else ("▼" if row["delta"] < 0 else " ")
        print(
            f"{row['dataset']:<22} "
            f"{row['before_rate']*100:>6.1f}% "
            f"{row['after_rate']*100:>6.1f}% "
            f"{d_arrow}{abs(row['delta'])*100:>5.1f}pp"
        )

    # regressions
    if regressions:
        print(f"\n{'='*65}")
        print(f"REGRESSIONS ({len(regressions)}) — queries that PASSED before but FAIL now:")
        print(f"{'-'*65}")
        for d in regressions:
            q_short = d.question[:55] + "..." if len(d.question) > 55 else d.question
            print(f"  ✗ {d.key}")
            print(f"    {q_short}")
            print(f"    Before: {d.before_rate*100:.0f}%  After: {d.after_rate*100:.0f}%")
    else:
        print(f"\n✓ No regressions")

    # improvements
    if improvements:
        print(f"\n{'='*65}")
        print(f"IMPROVEMENTS ({len(improvements)}) — queries that FAILED before but PASS now:")
        print(f"{'-'*65}")
        for d in improvements:
            q_short = d.question[:55] + "..." if len(d.question) > 55 else d.question
            print(f"  ✓ {d.key}")
            print(f"    {q_short}")
            print(f"    Before: {d.before_rate*100:.0f}%  After: {d.after_rate*100:.0f}%")
    else:
        print(f"\n  No new improvements")

    # unchanged summary
    still_pass = sum(1 for d in unchanged if d.after_pass)
    still_fail = sum(1 for d in unchanged if not d.after_pass)
    print(f"\n{'='*65}")
    print(f"Unchanged: {len(unchanged)} queries")
    print(f"  Still passing: {still_pass}")
    print(f"  Still failing: {still_fail}")
    print(f"{'='*65}\n")

    return len(regressions)


# ── JSON diff output ──────────────────────────────────────────────────────────

def to_json_report(
    baseline: dict,
    current:  dict,
    diffs:    list[QueryDiff],
    ds_diffs: list[dict],
) -> dict:
    """Return the full diff as a serializable dict for saving."""
    return {
        "baseline_run_id": baseline.get("run_id"),
        "current_run_id":  current.get("run_id"),
        "baseline_rate":   baseline.get("pass_rate"),
        "current_rate":    current.get("pass_rate"),
        "delta":           round((current.get("pass_rate", 0) - baseline.get("pass_rate", 0)), 4),
        "regressions":     [
            {"key": d.key, "question": d.question,
             "before_rate": d.before_rate, "after_rate": d.after_rate}
            for d in diffs if d.is_regression
        ],
        "improvements": [
            {"key": d.key, "question": d.question,
             "before_rate": d.before_rate, "after_rate": d.after_rate}
            for d in diffs if d.is_improvement
        ],
        "per_dataset": ds_diffs,
        "per_query":   [
            {
                "key":         d.key,
                "before_pass": d.before_pass,
                "after_pass":  d.after_pass,
                "before_rate": d.before_rate,
                "after_rate":  d.after_rate,
                "delta":       d.delta,
            }
            for d in diffs
        ],
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oracle Forge Regression Suite")
    parser.add_argument("--baseline", required=True, help="Path to baseline benchmark JSON")
    parser.add_argument("--current",  required=True, help="Path to current benchmark JSON")
    parser.add_argument(
        "--no_fail", action="store_true",
        help="Do not exit with code 1 when regressions are found",
    )
    parser.add_argument(
        "--save", type=str, default=None,
        help="Save the diff report to this JSON file path",
    )
    args = parser.parse_args()

    baseline = load_result(args.baseline)
    current  = load_result(args.current)

    diffs    = compute_diff(baseline, current)
    ds_diffs = compute_dataset_diff(baseline, current)

    n_regressions = print_report(baseline, current, diffs, ds_diffs)

    if args.save:
        report = to_json_report(baseline, current, diffs, ds_diffs)
        save_path = Path(args.save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Diff report saved: {save_path}")

    if n_regressions > 0 and not args.no_fail:
        sys.exit(1)
