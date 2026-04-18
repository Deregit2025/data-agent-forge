"""
Evaluation Harness — Oracle Forge

Runs OracleForgeAgent against all DAB queries and scores each answer.
Produces a structured JSON results file and a printed summary table.

Usage:
    # Run all datasets, 5 trials each (full benchmark)
    python -m eval.harness

    # Run a single dataset
    python -m eval.harness --datasets yelp

    # Run a single query (fast smoke test)
    python -m eval.harness --datasets yelp --query_ids 1 --n_trials 1

    # Run without hints
    python -m eval.harness --no_hints

Output:
    eval/results/benchmark_{run_id}.json   — full structured results
    eval/results/latest.json               — symlink/copy of the latest run

After a full run, autoDream consolidates any new corrections automatically.
"""

import os
import sys
import re
import json


class RateLimitError(RuntimeError):
    """Raised when the LLM API weekly key limit is exceeded. Aborts the benchmark."""
    pass
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

# ── paths ─────────────────────────────────────────────────────────────────────

ORACLE_ROOT = Path(__file__).parent.parent
DAB_ROOT    = Path(os.getenv("DAB_PATH", "/home/project/oracle-forge/DataAgentBench"))
RESULTS_DIR = ORACLE_ROOT / "eval" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ORACLE_ROOT))
sys.path.insert(0, str(DAB_ROOT))

from dotenv import load_dotenv
load_dotenv(ORACLE_ROOT / ".env")

from eval.scorer       import score
from eval.trace_schema import TrialResult, QueryResult, DatasetResult, BenchmarkResult

# ── logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("harness")

# ── dataset registry ──────────────────────────────────────────────────────────
# Maps DAB folder name → conductor dataset name (from agent/main.py DATASET_MAP)

DATASET_REGISTRY = {
    "yelp":             "yelp",
    "agnews":           "agnews",
    "bookreview":       "bookreview",
    "crmarenapro":      "crmarenapro",
    "DEPS_DEV_V1":      "deps_dev",
    "GITHUB_REPOS":     "github_repos",
    "googlelocal":      "googlelocal",
    "music_brainz_20k": "music_brainz",
    "PANCANCER_ATLAS":  "pancancer",
    "PATENTS":          "patents",
    "stockindex":       "stockindex",
    "stockmarket":      "stockmarket",
}


# ── query discovery ───────────────────────────────────────────────────────────

def discover_queries(dataset_folder: str) -> list[int]:
    """
    Find all queryN directories for a dataset.
    Returns sorted list of query IDs (integers).
    Excludes query_dataset and any non-numeric dirs.
    """
    dataset_dir = DAB_ROOT / f"query_{dataset_folder}"
    if not dataset_dir.exists():
        logger.warning(f"Dataset directory not found: {dataset_dir}")
        return []

    query_ids = []
    for d in dataset_dir.iterdir():
        m = re.match(r'^query(\d+)$', d.name)
        if m and d.is_dir():
            query_ids.append(int(m.group(1)))

    return sorted(query_ids)


def load_question(query_dir: Path) -> str:
    """Load the question text from query.json."""
    query_json = query_dir / "query.json"
    with open(query_json, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, str):
        return data
    if isinstance(data, dict) and "query" in data:
        return data["query"]
    raise ValueError(f"Unrecognized query.json format: {data}")


# ── single trial runner ───────────────────────────────────────────────────────

def run_trial(
    dataset_folder: str,
    dataset_name:   str,
    query_id:       int,
    trial_num:      int,
    use_hints:      bool = True,
) -> TrialResult:
    """
    Run one trial of OracleForgeAgent on a single query.
    Returns a TrialResult with the answer and validation score.
    """
    from agent.main import OracleForgeAgent

    dataset_dir = DAB_ROOT / f"query_{dataset_folder}"
    query_dir   = dataset_dir / f"query{query_id}"
    run_id      = f"trial_{trial_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    question = load_question(query_dir)
    logger.info(f"  Trial {trial_num}: {dataset_folder}/query{query_id}")

    # load db description
    db_description = (dataset_dir / "db_description.txt").read_text(encoding="utf-8").strip()
    if use_hints:
        hint_path = dataset_dir / "db_description_withhint.txt"
        if hint_path.exists():
            db_description += "\n\n" + hint_path.read_text(encoding="utf-8").strip()

    start = time.perf_counter()
    answer = ""
    error  = None
    steps  = []

    try:
        agent = OracleForgeAgent(
            query_dir=query_dir,
            db_description=db_description,
            db_config_path=str(dataset_dir / "db_config.yaml"),
            max_iterations=10,
            root_name=run_id,
        )
        answer = agent.run() or ""

        # extract compact step trace from agent for embedding in benchmark JSON
        for step in getattr(agent, "trace", []):
            node = step.get("node", "")
            if node == "plan":
                plan = step.get("plan", {})
                steps.append({
                    "node":      "plan",
                    "reasoning": plan.get("reasoning", ""),
                    "step_count": len(plan.get("steps", [])),
                    "tools_planned": [s.get("tool_name") for s in plan.get("steps", [])],
                })
            elif node == "execute":
                steps.append({
                    "node":       "execute",
                    "step":       step.get("step"),
                    "tool_name":  step.get("tool_name"),
                    "db_type":    step.get("db_type"),
                    "query_used": step.get("query_used", ""),
                    "row_count":  step.get("row_count", 0),
                    "error":      step.get("error"),
                })
            elif node == "correct":
                steps.append({
                    "node":      "correct",
                    "tool_name": step.get("tool_name"),
                    "fix":       step.get("fix", ""),
                    "row_count": step.get("row_count", 0),
                    "error":     step.get("error"),
                })
            elif node == "synthesize":
                steps.append({
                    "node":   "synthesize",
                    "answer": step.get("answer", ""),
                })
    except Exception as e:
        error  = f"{type(e).__name__}: {e}"
        logger.error(f"    Agent error: {error}")

    elapsed = round(time.perf_counter() - start, 2)

    # detect hard API rate limit — abort entire benchmark immediately
    if "Key limit exceeded" in (answer or "") or "Key limit exceeded" in (error or ""):
        raise RateLimitError(
            "OpenRouter weekly key limit exceeded. "
            "Renew at https://openrouter.ai/settings/keys then re-run."
        )

    # score the answer
    score_result = score(answer, query_dir)

    logger.info(
        f"    {'PASS' if score_result['is_valid'] else 'FAIL'} "
        f"({elapsed}s) — {score_result['reason']}"
    )

    return TrialResult(
        dataset=      dataset_name,
        query_id=     query_id,
        trial_num=    trial_num,
        question=     question,
        answer=       answer,
        is_valid=     score_result["is_valid"],
        reason=       score_result["reason"],
        ground_truth= score_result["ground_truth"],
        elapsed_s=    elapsed,
        root_name=    run_id,
        error=        error,
        steps=        steps,
    )


# ── query runner (n trials) ───────────────────────────────────────────────────

def run_query(
    query_id:       int,
    n_trials:       int = 5,
    use_hints:      bool = True,
    no_early_stop:  bool = False,
) -> QueryResult:
    """Run n_trials trials for a single query and return aggregated QueryResult."""
    query_dir    = DAB_ROOT / f"query_{dataset_folder}" / f"query{query_id}"
    question     = load_question(query_dir)
    gt_path      = query_dir / "ground_truth.csv"
    ground_truth = gt_path.read_text(encoding="utf-8").strip() if gt_path.exists() else ""

    qr = QueryResult(
        dataset=      dataset_name,
        query_id=     query_id,
        question=     question,
        ground_truth= ground_truth,
    )

    for t in range(1, n_trials + 1):
        trial = run_trial(dataset_folder, dataset_name, query_id, t, use_hints)
        qr.trials.append(trial)

        # early exit if we already have a majority (saves API calls)
         # early exit if we already have a majority (saves API calls)
        if not no_early_stop:
            remaining = n_trials - t
            if qr.pass_count > n_trials / 2:
                logger.info(f"    Majority reached ({qr.pass_count}/{t}), skipping {remaining} remaining trials")
                break
            if qr.pass_count == 0 and remaining < (n_trials - qr.pass_count):
                needed = (n_trials // 2) + 1
                if qr.pass_count + remaining < needed:
                    logger.info(f"    Can't reach majority, skipping {remaining} remaining trials")
                    break

    logger.info(
        f"  Query {query_id} summary: {qr.pass_count}/{qr.n_trials} passed "
        f"({'MAJORITY PASS' if qr.majority_pass else 'FAIL'})"
    )
    return qr


# ── dataset runner ────────────────────────────────────────────────────────────

def run_dataset(
    dataset_folder: str,
    query_ids:      list[int] | None = None,
    n_trials:       int  = 5,
    use_hints:      bool = True,
    no_early_stop:  bool = False,
) -> tuple[DatasetResult, list[QueryResult]]:
    """Run all queries for one dataset. Returns (DatasetResult, list[QueryResult])."""
    dataset_name = DATASET_REGISTRY.get(dataset_folder, dataset_folder)

    if query_ids is None:
        query_ids = discover_queries(dataset_folder)

    if not query_ids:
        logger.warning(f"No queries found for dataset: {dataset_folder}")
        return DatasetResult(dataset_folder, 0, 0, 0, 0.0), []

    logger.info(f"\n{'='*60}")
    logger.info(f"Dataset: {dataset_folder} ({len(query_ids)} queries, {n_trials} trials each)")
    logger.info(f"{'='*60}")

    query_results = []
    for qid in query_ids:
        qr = run_query(dataset_folder, dataset_name, qid, n_trials, use_hints, no_early_stop)
        query_results.append(qr)

    pass_count     = sum(1 for qr in query_results if qr.majority_pass)
    any_pass_count = sum(1 for qr in query_results if qr.any_pass)
    pass_rate      = round(pass_count / len(query_results), 4) if query_results else 0.0

    ds_result = DatasetResult(
        dataset=        dataset_name,
        n_queries=      len(query_results),
        pass_count=     pass_count,
        any_pass_count= any_pass_count,
        pass_rate=      pass_rate,
    )

    logger.info(
        f"\nDataset {dataset_folder}: {pass_count}/{len(query_results)} queries passed "
        f"({pass_rate*100:.1f}%)"
    )
    return ds_result, query_results


# ── benchmark runner ──────────────────────────────────────────────────────────

def run_benchmark(
    datasets:      list[str] | None = None,
    query_ids:     list[int] | None = None,
    n_trials:      int  = 5,
    use_hints:     bool = True,
    model:         str  = "claude-sonnet-4.6",
    no_early_stop: bool = False,
) -> BenchmarkResult:
    """
    Run the full benchmark across all datasets and queries.

    Args:
        datasets:  list of dataset folder names to run (default: all)
        query_ids: specific query IDs to run (applied to all datasets; default: all)
        n_trials:  number of trials per query (default: 5)
        use_hints: whether to load db_description_withhint.txt (default: True)
        model:     model name for reporting

    Returns:
        BenchmarkResult with full structured results
    """
    if datasets is None:
        datasets = list(DATASET_REGISTRY.keys())

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"\nOracle Forge Benchmark — run_id: {run_id}")
    logger.info(f"Datasets: {datasets}")
    logger.info(f"Trials per query: {n_trials}")

    all_query_results   = []
    all_dataset_results = []

    for ds_folder in datasets:
        try:
            ds_result, qrs = run_dataset(ds_folder, query_ids, n_trials, use_hints, no_early_stop)
        except RateLimitError as e:
            logger.error(f"\n{'='*60}")
            logger.error(f"RATE LIMIT HIT — stopping benchmark early.")
            logger.error(str(e))
            logger.error(f"{'='*60}\n")
            break
        all_dataset_results.append(ds_result)
        all_query_results.extend(qrs)

    total_queries = sum(d.n_queries for d in all_dataset_results)
    total_pass    = sum(d.pass_count for d in all_dataset_results)
    overall_rate  = round(total_pass / total_queries, 4) if total_queries else 0.0

    benchmark = BenchmarkResult(
        run_id=        run_id,
        n_trials=      n_trials,
        model=         model,
        total_queries= total_queries,
        pass_count=    total_pass,
        pass_rate=     overall_rate,
        per_dataset=   all_dataset_results,
        per_query=     all_query_results,
    )

    return benchmark


# ── results persistence ───────────────────────────────────────────────────────

def save_results(benchmark: BenchmarkResult) -> Path:
    """Save benchmark results to eval/results/ and update latest.json."""
    out_path = RESULTS_DIR / f"benchmark_{benchmark.run_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(benchmark.to_dict(), f, indent=2)
    logger.info(f"\nResults saved: {out_path}")

    # overwrite latest.json
    latest_path = RESULTS_DIR / "latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(benchmark.to_dict(), f, indent=2)

    return out_path


# ── summary printer ───────────────────────────────────────────────────────────

def print_summary(benchmark: BenchmarkResult):
    """Print a readable summary table to stdout."""
    print(f"\n{'='*60}")
    print(f"ORACLE FORGE BENCHMARK RESULTS — {benchmark.run_id}")
    print(f"{'='*60}")
    print(f"Model:          {benchmark.model}")
    print(f"Trials/query:   {benchmark.n_trials}")
    print(f"Total queries:  {benchmark.total_queries}")
    print(f"Total passed:   {benchmark.pass_count} ({benchmark.pass_rate*100:.1f}%)")
    print(f"{'='*60}")
    print(f"\n{'Dataset':<22} {'Queries':>7} {'Passed':>7} {'Pass%':>7} {'AnyPass':>8}")
    print(f"{'-'*55}")

    for ds in benchmark.per_dataset:
        print(
            f"{ds.dataset:<22} {ds.n_queries:>7} {ds.pass_count:>7} "
            f"{ds.pass_rate*100:>6.1f}% {ds.any_pass_count:>8}"
        )

    print(f"{'-'*55}")
    print(f"{'TOTAL':<22} {benchmark.total_queries:>7} {benchmark.pass_count:>7} "
          f"{benchmark.pass_rate*100:>6.1f}%")
    print(f"\n{'='*60}\n")

    # per-query detail
    print("Per-query results:")
    print(f"{'Dataset':<22} {'QID':>4} {'Pass':>5} {'Rate':>6}  Question (truncated)")
    print(f"{'-'*80}")
    for qr in benchmark.per_query:
        status = "PASS" if qr.majority_pass else "FAIL"
        q_short = qr.question[:45] + "..." if len(qr.question) > 45 else qr.question
        print(
            f"{qr.dataset:<22} {qr.query_id:>4} {status:>5} "
            f"{qr.pass_rate*100:>5.0f}%  {q_short}"
        )


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oracle Forge Evaluation Harness")
    parser.add_argument(
        "--datasets", nargs="+",
        default=None,
        choices=list(DATASET_REGISTRY.keys()),
        help="Datasets to evaluate (default: all)",
    )
    parser.add_argument(
        "--query_ids", nargs="+", type=int,
        default=None,
        help="Specific query IDs to run (default: all in each dataset)",
    )
    parser.add_argument(
        "--n_trials", type=int, default=5,
        help="Number of trials per query (default: 5)",
    )
    parser.add_argument(
        "--no_hints", action="store_true",
        help="Disable loading db_description_withhint.txt",
    )
    parser.add_argument(
        "--model", type=str, default="claude-sonnet-4.6",
        help="Model name for reporting",
    )
    parser.add_argument(
        "--no_autodream", action="store_true",
        help="Skip autoDream consolidation after the run",
    )
    parser.add_argument(
        "--no_early_stop", action="store_true",
        help="Disable early stopping — run all n_trials regardless of majority",
    )
    args = parser.parse_args()

    benchmark = run_benchmark(
        datasets=  args.datasets,
        query_ids= args.query_ids,
        n_trials=  args.n_trials,
        use_hints= not args.no_hints,
        model=     args.model,
    )

    out_path = save_results(benchmark)
    print_summary(benchmark)

    # run autoDream to consolidate any new corrections
    if not args.no_autodream:
        logger.info("Running autoDream consolidation...")
        try:
            from utils.autodream import consolidate
            consolidate()
        except Exception as e:
            logger.warning(f"autoDream failed: {e}")

    print(f"\nFull results: {out_path}")
