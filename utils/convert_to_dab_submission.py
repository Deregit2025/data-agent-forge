"""
Convert Oracle Forge harness output to DAB leaderboard submission format.
Usage: python utils/convert_to_dab_submission.py
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
    "music_brainz_20k": "music_brainz_20k",
    "PANCANCER_ATLAS":  "pancancer_atlas",
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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, default=None)
    args = parser.parse_args()

    if args.file:
        latest = Path(args.file)
    else:
        result_files = sorted(RESULTS_DIR.glob("benchmark_*.json"), reverse=True)
        if not result_files:
            print("No results files found in eval/results/")
            exit(1)
        # Find the file with most queries
        latest = max(result_files, key=lambda f: json.load(open(f)).get("total_queries", 0))

    print(f"Converting: {latest.name}")

    submission = convert(latest)
    print(f"Total entries: {len(submission)}")

    datasets = set(e["dataset"] for e in submission)
    queries_per_dataset = {}
    for e in submission:
        key = f"{e['dataset']}_Q{e['query']}"
        queries_per_dataset[key] = queries_per_dataset.get(key, 0) + 1

    print(f"Datasets covered: {len(datasets)}")
    print(f"Unique queries: {len(queries_per_dataset)}")
    print(f"Trials per query: {list(queries_per_dataset.values())[0] if queries_per_dataset else 0}")

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(submission, f, indent=2)

    print(f"Saved to: {OUTPUT_FILE}")
    print("\nSample entries:")
    for e in submission[:3]:
        print(f"  {e}")