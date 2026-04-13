"""
Oracle Forge Agent — Main Entry Point
Connects our conductor agent to DAB's evaluation framework.

This file is what DAB's run_agent.py calls instead of DataAgent.
It reads the query, loads three-layer context, runs the conductor,
and returns a structured answer in DAB's expected format.

Usage (via DAB evaluation):
    python run_oracle.py \
        --dataset yelp \
        --query_id 1 \
        --iterations 5 \
        --root_name run_0

Usage (direct):
    python -m agent.main --dataset yelp --query_id 1
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ── paths ─────────────────────────────────────────────────────────────────────

ORACLE_ROOT = Path(__file__).parent.parent
DAB_PATH    = os.getenv("DAB_PATH", "/home/project/oracle-forge/DataAgentBench")

load_dotenv(ORACLE_ROOT / ".env")

sys.path.insert(0, str(ORACLE_ROOT))
sys.path.insert(0, DAB_PATH)

# ── logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("oracle_forge")

# ── dataset to conductor dataset name mapping ─────────────────────────────────

DATASET_MAP = {
    "yelp":            "yelp",
    "agnews":          "agnews",
    "bookreview":      "bookreview",
    "crmarenapro":     "crmarenapro",
    "DEPS_DEV_V1":     "deps_dev",
    "GITHUB_REPOS":    "github_repos",
    "googlelocal":     "googlelocal",
    "music_brainz_20k":"music_brainz",
    "PANCANCER_ATLAS": "pancancer",
    "PATENTS":         "patents",
    "stockindex":      "stockindex",
    "stockmarket":     "stockmarket",
}


# ── Oracle Forge Agent class ──────────────────────────────────────────────────

class OracleForgeAgent:
    """
    Drop-in replacement for DAB's DataAgent.
    Uses our conductor + sub-agent architecture instead of DAB's built-in agent.
    """

    def __init__(
        self,
        query_dir:           Path,
        db_description:      str,
        db_config_path:      str,
        deployment_name:     str = "claude-sonnet-4.6",
        exec_python_timeout: int = 600,
        max_iterations:      int = 10,
        root_name:           str = None,
    ):
        self.query_dir       = Path(query_dir)
        self.db_description  = db_description
        self.db_config_path  = db_config_path
        self.deployment_name = deployment_name
        self.max_iterations  = max_iterations
        self.root_name       = root_name or datetime.now().strftime("%Y%m%d_%H%M%S")

        # derive dataset name from query_dir path
        # query_dir is like: DataAgentBench/query_yelp/query1
        dataset_folder = self.query_dir.parent.name  # e.g. query_yelp
        raw_dataset    = dataset_folder.replace("query_", "")  # e.g. yelp
        self.dataset   = DATASET_MAP.get(raw_dataset, raw_dataset)

        # set up run directory for logs
        self.root_dir = self.query_dir / "logs" / "oracle_forge" / self.root_name
        self.root_dir.mkdir(parents=True, exist_ok=True)

        # load query
        query_file = self.query_dir / "query.json"
        with open(query_file, encoding="utf-8") as f:
            query_info = json.load(f)

        if isinstance(query_info, str):
            self.question = query_info
        elif isinstance(query_info, dict) and "query" in query_info:
            self.question = query_info["query"]
        else:
            raise ValueError(f"Unrecognized query.json format: {query_info}")

        # agent state
        self.final_result    = None
        self.terminate_reason = None
        self.trace           = []

        logger.info(f"OracleForgeAgent initialized")
        logger.info(f"  Dataset:  {self.dataset}")
        logger.info(f"  Question: {self.question}")
        logger.info(f"  Root dir: {self.root_dir}")


    def run(self) -> str:
        """
        Run the conductor agent on the question.
        Returns the final answer as a string.
        """
        from agent.conductor import run as conductor_run

        logger.info("Starting Oracle Forge conductor...")
        start = time.perf_counter()

        result = conductor_run(
            question=self.question,
            dataset=self.dataset,
        )

        elapsed = round(time.perf_counter() - start, 2)
        logger.info(f"Conductor completed in {elapsed}s")

        self.final_result     = result.get("answer", "")
        self.terminate_reason = "return_answer" if self.final_result else "max_iterations"
        self.trace            = result.get("trace", [])

        # save logs in DAB-compatible format
        self._save_logs(result, elapsed)

        return self.final_result


    def _save_logs(self, result: dict, elapsed: float):
        """Save run logs in DAB-compatible format."""

        # final_agent.json — matches DAB's expected format
        final_log = {
            "final_result":    self.final_result,
            "terminate_reason": self.terminate_reason,
            "dataset":         self.dataset,
            "question":        self.question,
            "elapsed_seconds": elapsed,
            "trace":           self.trace,
            "agent":           "oracle_forge",
            "model":           self.deployment_name,
            "timestamp":       datetime.now().isoformat(),
        }

        with open(self.root_dir / "final_agent.json", "w") as f:
            json.dump(final_log, f, indent=2)

        # tool_calls.jsonl — one line per trace step
        with open(self.root_dir / "tool_calls.jsonl", "w") as f:
            for step in self.trace:
                f.write(json.dumps(step) + "\n")

        logger.info(f"Logs saved to {self.root_dir}")


    def to_dict(self) -> dict:
        """Return agent state as dict — matches DAB's DataAgent.to_dict()."""
        return {
            "final_result":    self.final_result,
            "terminate_reason": self.terminate_reason,
            "dataset":         self.dataset,
            "question":        self.question,
            "trace":           self.trace,
        }


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from argparse import ArgumentParser

    DATASET_LIST = list(DATASET_MAP.keys())

    parser = ArgumentParser(description="Oracle Forge Agent")
    parser.add_argument("--dataset",    type=str, required=True, choices=DATASET_LIST)
    parser.add_argument("--query_id",   type=int, required=True)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--use_hints",  action="store_true")
    parser.add_argument("--root_name",  type=str, default=None)
    args = parser.parse_args()

    dab_path  = Path(DAB_PATH)
    db_dir    = dab_path / f"query_{args.dataset}"
    query_dir = db_dir / f"query{args.query_id}"

    if not query_dir.exists():
        raise ValueError(f"Query directory not found: {query_dir}")

    db_description = (db_dir / "db_description.txt").read_text().strip()
    if args.use_hints:
        hint_path = db_dir / "db_description_withhint.txt"
        if hint_path.exists():
            db_description += "\n\n" + hint_path.read_text().strip()

    agent = OracleForgeAgent(
        query_dir=query_dir,
        db_description=db_description,
        db_config_path=str(db_dir / "db_config.yaml"),
        max_iterations=args.iterations,
        root_name=args.root_name,
    )

    answer = agent.run()
    print(f"\nAnswer: {answer}")