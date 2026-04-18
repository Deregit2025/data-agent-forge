"""
Convert Oracle Forge harness output to DAB leaderboard submission format.
Usage: 
  python utils/convert_to_dab_submission.py
  python utils/convert_to_dab_submission.py --file eval/results/benchmark_XXX.json
  python utils/convert_to_dab_submission.py --merge eval/results/file1.json eval/results/file2.json
"""
import json
import os
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "eval" / "results"
OUTPUT_FILE = Path(__file__).parent.parent / "results" / "dab_submission.json"

# DAB dataset name mapping (harness name -> DAB name)
DATASET_MAP = {
    "yelp":             "yelp",
    "googlelocal":      "googlelocal",
    "stockmarket":      "stockmarket",
    "stockindex":       "stockindex",
    "agnews":           "agnews",
    "bookreview":       "bookreview",
    "crmarenapro":      "crmarenapro",
    "deps_dev":         "deps_dev_v1",
    "DEPS_DEV_V1":      "deps_dev_v1",
    "github_repos":     "github_repos",
    "GITHUB_REPOS":     "github_repos",
    "music_brainz":     "music_brainz_20k",
    "music_brainz_20k": "music_brainz_20k",
    "PANCANCER_ATLAS":  "pancancer_atlas",
    "pancancer":        "pancancer_atlas",
    "pancancer_atlas":  "pancancer_atlas",
    "PATENTS":          "patents",
    "patents":          "patents",
}


def convert(results_file: Path) -> list:
    with open(results_file) as f:
        data = json.load(f)

    submission = []
    for query_result in data.get("per_query", []):
        dataset_raw = query_result["dataset"]
        dataset = DATASET_MAP.get(dataset_raw, dataset_raw.lower())
        query_id = str(query_result["query_id"])

        for trial in query_result.get("trials", []):
            run_num = trial["trial_num"] - 1  # DAB uses 0-indexed runs
            answer = trial.get("answer", "N/A") or "N/A"
            submission.append({
                "dataset": dataset,
                "query":   query_id,
                "run":     str(run_num),
                "answer":  answer
            })

    return submission


def convert_multiple(result_files: list) -> list:
    """Merge multiple benchmark result files into one submission."""
    run_counters = {}  # key: (dataset, query) -> next run number
    entries = {}       # key: (dataset, query, run) -> answer

    for result_file in result_files:
        with open(result_file) as f:
            data = json.load(f)

        for query_result in data.get("per_query", []):
            dataset_raw = query_result["dataset"]
            dataset = DATASET_MAP.get(dataset_raw, dataset_raw.lower())
            query_id = str(query_result["query_id"])
            key = (dataset, query_id)

            if key not in run_counters:
                run_counters[key] = 0

            for trial in query_result.get("trials", []):
                run_num = run_counters[key]
                answer = trial.get("answer", "N/A") or "N/A"
                entries[(dataset, query_id, str(run_num))] = answer
                run_counters[key] += 1

    return [
        {"dataset": k[0], "query": k[1], "run": k[2], "answer": v}
        for k, v in sorted(entries.items())
    ]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, default=None, help="Single result file to convert")
    parser.add_argument("--merge", nargs="+", type=str, default=None, help="Multiple result files to merge")
    args = parser.parse_args()

    if args.merge:
        files = [Path(f) for f in args.merge]
        print(f"Merging {len(files)} files...")
        submission = convert_multiple(files)
    elif args.file:
        latest = Path(args.file)
        print(f"Converting: {latest.name}")
        submission = convert(latest)
    else:
        result_files = sorted(RESULTS_DIR.glob("benchmark_*.json"), reverse=True)
        if not result_files:
            print("No results files found in eval/results/")
            exit(1)
        latest = max(result_files, key=lambda f: json.load(open(f)).get("total_queries", 0))
        print(f"Converting: {latest.name}")
        submission = convert(latest)

    print(f"Total entries: {len(submission)}")

    # Stats
    datasets = set(e["dataset"] for e in submission)
    queries_per_dataset = {}
    for e in submission:
        k = f"{e['dataset']}_Q{e['query']}"
        queries_per_dataset[k] = queries_per_dataset.get(k, 0) + 1

    print(f"Datasets covered: {len(datasets)}")
    print(f"Unique queries: {len(queries_per_dataset)}")

    low = {k: v for k, v in queries_per_dataset.items() if v < 5}
    if low:
        print(f"Queries with < 5 trials: {len(low)}")
        for k, v in sorted(low.items()):
            print(f"  {k}: {v} trials")
    else:
        print("All queries have >= 5 trials ✅")

    # Save
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(submission, f, indent=2)

    print(f"\nSaved to: {OUTPUT_FILE}")
    print("\nSample entries:")
    for e in submission[:3]:
        print(f"  {e}")