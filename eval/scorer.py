"""
Scorer — Oracle Forge Evaluation Framework

Scores an agent answer against a query's validate.py.
Mirrors the DAB common_scaffold validate approach exactly:
  - dynamically loads query_dir/validate.py
  - calls validate(llm_output) -> (bool, str)
  - returns a structured result dict

Usage:
    from eval.scorer import score

    result = score(
        answer="The average rating is 3.55",
        query_dir=Path("/home/project/oracle-forge/DataAgentBench/query_yelp/query1"),
    )
    # result = {"is_valid": True, "reason": "...", "ground_truth": "3.547...", "llm_answer": "..."}
"""

import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def score(answer: str, query_dir: Path) -> dict:
    """
    Score an agent answer against the query's validate.py.

    Args:
        answer:    the agent's final answer string
        query_dir: path to the query directory (contains validate.py + ground_truth.csv)

    Returns:
        {
            "is_valid":     bool,
            "reason":       str,
            "ground_truth": str,
            "llm_answer":   str,
        }
    """
    query_dir = Path(query_dir)

    # read ground truth for logging (validate.py hardcodes it, but we read for records)
    gt_path = query_dir / "ground_truth.csv"
    if gt_path.exists():
        ground_truth = gt_path.read_text(encoding="utf-8").strip()
    else:
        ground_truth = "<ground_truth.csv missing>"
        logger.warning(f"ground_truth.csv not found: {gt_path}")

    # empty answer always fails
    if not answer or not answer.strip():
        return {
            "is_valid":     False,
            "reason":       "Empty answer — agent returned nothing",
            "ground_truth": ground_truth,
            "llm_answer":   "",
        }

    # load and call the query's validate.py
    validate_py = query_dir / "validate.py"
    if not validate_py.exists():
        logger.error(f"validate.py not found: {validate_py}")
        return {
            "is_valid":     False,
            "reason":       f"validate.py not found at {validate_py}",
            "ground_truth": ground_truth,
            "llm_answer":   answer.strip(),
        }

    try:
        spec = importlib.util.spec_from_file_location("validate_query", str(validate_py))
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        is_valid, reason = mod.validate(answer)
    except Exception as e:
        logger.error(f"validate.py raised exception for {query_dir.name}: {e}")
        return {
            "is_valid":     False,
            "reason":       f"Validation exception: {e}",
            "ground_truth": ground_truth,
            "llm_answer":   answer.strip(),
        }

    return {
        "is_valid":     bool(is_valid),
        "reason":       str(reason),
        "ground_truth": ground_truth,
        "llm_answer":   answer.strip(),
    }


def score_batch(answers: list[str], query_dir: Path) -> list[dict]:
    """Score multiple answers against the same query. Convenience wrapper."""
    return [score(a, query_dir) for a in answers]


def pass_rate(results: list[dict]) -> float:
    """Compute pass rate from a list of score() results."""
    if not results:
        return 0.0
    return round(sum(1 for r in results if r["is_valid"]) / len(results), 4)
