"""
Contract Validator — Week 7 pattern applied to agent outputs.
Validates the agent's final answer before returning it to the user.

Three validation modes (from Week 7):
  ENFORCE — block the answer if validation fails
  WARN    — log the issue but return the answer
  AUDIT   — record the issue silently

Validation checks:
  1. Answer is not empty
  2. Answer contains a concrete value (number, name, or fact)
  3. Answer does not contradict the query results
  4. Answer format matches the question type
"""

import re
import json
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ValidationMode(Enum):
    ENFORCE = "ENFORCE"
    WARN    = "WARN"
    AUDIT   = "AUDIT"


class ValidationStatus(Enum):
    PASS    = "PASS"
    WARN    = "WARN"
    FAIL    = "FAIL"


@dataclass
class ValidationResult:
    status:   ValidationStatus
    mode:     ValidationMode
    checks:   list[dict]
    answer:   str
    blocked:  bool = False
    message:  str  = ""


# ── main validator ────────────────────────────────────────────────────────────

def validate(
    answer:       str,
    question:     str,
    tool_results: list[dict],
    mode:         ValidationMode = ValidationMode.WARN,
) -> ValidationResult:
    """
    Validate an agent answer against the question and tool results.

    Args:
        answer:       the agent's final answer string
        question:     the original question asked
        tool_results: list of MCP tool results used to produce the answer
        mode:         ENFORCE, WARN, or AUDIT

    Returns:
        ValidationResult with status, checks, and whether answer is blocked
    """
    checks  = []
    failed  = []
    warned  = []

    # check 1 — answer is not empty
    c1 = _check_not_empty(answer)
    checks.append(c1)
    if c1["status"] == "FAIL":
        failed.append(c1)

    # check 2 — answer contains a concrete value
    c2 = _check_has_concrete_value(answer, question)
    checks.append(c2)
    if c2["status"] == "FAIL":
        failed.append(c2)
    elif c2["status"] == "WARN":
        warned.append(c2)

    # check 3 — answer is consistent with tool results
    c3 = _check_consistent_with_results(answer, tool_results)
    checks.append(c3)
    if c3["status"] == "FAIL":
        failed.append(c3)
    elif c3["status"] == "WARN":
        warned.append(c3)

    # check 4 — answer format matches question type
    c4 = _check_format_matches_question(answer, question)
    checks.append(c4)
    if c4["status"] == "WARN":
        warned.append(c4)

    # determine overall status
    if failed:
        overall_status = ValidationStatus.FAIL
    elif warned:
        overall_status = ValidationStatus.WARN
    else:
        overall_status = ValidationStatus.PASS

    # determine if answer is blocked
    blocked = False
    if mode == ValidationMode.ENFORCE and overall_status == ValidationStatus.FAIL:
        blocked = True
        message = f"Answer blocked by ENFORCE mode. Failed checks: {[c['name'] for c in failed]}"
    elif overall_status == ValidationStatus.WARN:
        message = f"Validation warnings: {[c['name'] for c in warned]}"
    else:
        message = "Validation passed"

    return ValidationResult(
        status=overall_status,
        mode=mode,
        checks=checks,
        answer=answer,
        blocked=blocked,
        message=message,
    )


def validate_and_enforce(
    answer:       str,
    question:     str,
    tool_results: list[dict],
) -> str:
    """
    Validate in ENFORCE mode. Returns answer if valid, raises if blocked.
    Used by conductor before returning final answer.
    """
    result = validate(answer, question, tool_results, ValidationMode.ENFORCE)
    if result.blocked:
        raise ValueError(f"Contract violation: {result.message}")
    return answer


# ── individual checks ─────────────────────────────────────────────────────────

def _check_not_empty(answer: str) -> dict:
    if not answer or not answer.strip():
        return {
            "name":    "not_empty",
            "status":  "FAIL",
            "message": "Answer is empty",
        }
    return {"name": "not_empty", "status": "PASS", "message": "Answer is not empty"}


def _check_has_concrete_value(answer: str, question: str) -> dict:
    """Check that the answer contains a number, name, or specific fact."""

    # questions expecting a number
    numeric_keywords = ["average", "count", "how many", "total", "sum",
                        "percent", "rate", "price", "amount", "score"]
    expects_number   = any(kw in question.lower() for kw in numeric_keywords)

    has_number = bool(re.search(r'\d+\.?\d*', answer))

    if expects_number and not has_number:
        return {
            "name":    "has_concrete_value",
            "status":  "WARN",
            "message": "Question expects a numeric answer but none found",
        }

    # check answer is not just a refusal
    refusal_patterns = [
        "cannot be determined", "not available", "no data",
        "unable to", "not possible", "i don't know",
        "cannot calculate", "no results found",
    ]
    is_refusal = any(p in answer.lower() for p in refusal_patterns)

    if is_refusal and len(answer) < 200:
        return {
            "name":    "has_concrete_value",
            "status":  "WARN",
            "message": "Answer appears to be a refusal without a concrete value",
        }

    return {
        "name":    "has_concrete_value",
        "status":  "PASS",
        "message": "Answer contains a concrete value",
    }


def _check_consistent_with_results(answer: str, tool_results: list[dict]) -> dict:
    """Check answer is consistent with what the tools actually returned."""

    if not tool_results:
        return {
            "name":    "consistent_with_results",
            "status":  "WARN",
            "message": "No tool results to validate against",
        }

    # check if all tools returned errors or empty results
    all_empty = all(
        r.get("row_count", 0) == 0 or r.get("error")
        for r in tool_results
    )

    if all_empty:
        # answer should acknowledge no data was found
        acknowledges_empty = any(
            phrase in answer.lower()
            for phrase in ["no ", "not found", "no data", "empty", "0 ", "zero"]
        )
        if not acknowledges_empty:
            return {
                "name":    "consistent_with_results",
                "status":  "WARN",
                "message": "All tools returned empty results but answer does not acknowledge this",
            }

    # check numbers in answer against numbers in results
    answer_numbers = set(re.findall(r'\d+\.?\d*', answer))
    result_numbers = set()
    for r in tool_results:
        result_text = json.dumps(r.get("result", []))
        result_numbers.update(re.findall(r'\d+\.?\d*', result_text))

    if answer_numbers and result_numbers:
        overlap = answer_numbers & result_numbers
        if not overlap and len(answer_numbers) > 0:
            return {
                "name":    "consistent_with_results",
                "status":  "WARN",
                "message": "Numbers in answer do not appear in tool results",
            }

    return {
        "name":    "consistent_with_results",
        "status":  "PASS",
        "message": "Answer is consistent with tool results",
    }


def _check_format_matches_question(answer: str, question: str) -> dict:
    """Check answer format is appropriate for the question type."""

    q = question.lower()

    # yes/no questions
    if q.startswith(("is ", "are ", "does ", "do ", "has ", "have ", "can ", "did ")):
        has_yes_no = any(
            w in answer.lower()
            for w in ["yes", "no", "true", "false", "correct", "incorrect"]
        )
        if not has_yes_no:
            return {
                "name":    "format_matches_question",
                "status":  "WARN",
                "message": "Yes/no question but answer does not contain yes or no",
            }

    # list questions
    if any(kw in q for kw in ["list", "what are", "which", "name all"]):
        has_list = (
            "\n" in answer or
            "," in answer or
            any(str(i) + "." in answer for i in range(1, 5))
        )
        if not has_list and len(answer) < 100:
            return {
                "name":    "format_matches_question",
                "status":  "WARN",
                "message": "List question but answer does not appear to be a list",
            }

    return {
        "name":    "format_matches_question",
        "status":  "PASS",
        "message": "Answer format matches question type",
    }


# ── convenience serializer ────────────────────────────────────────────────────

def to_dict(result: ValidationResult) -> dict:
    return {
        "status":   result.status.value,
        "mode":     result.mode.value,
        "blocked":  result.blocked,
        "message":  result.message,
        "checks":   result.checks,
    }