"""
Typed Failure Taxonomy
Classifies every database query failure into a specific type
so the recovery router can apply the correct fix strategy.

Each failure type maps to a specific recovery approach.
This avoids generic retry logic and makes self-correction precise.
"""

from enum import Enum


class FailureType(Enum):
    """
    Typed failure categories for database query errors.
    Each type has a specific recovery strategy in recovery_router.py
    """

    # SQL syntax error — wrong SQL dialect, typo, bad column name
    QUERY_SYNTAX_ERROR      = "query_syntax_error"

    # Join key format mismatch — businessid_ vs businessref_ etc
    JOIN_KEY_MISMATCH       = "join_key_mismatch"

    # Wrong database type — sent SQL to MongoDB or pipeline to PostgreSQL
    DATABASE_TYPE_ERROR     = "database_type_error"

    # Query returned empty results — filters too strict or wrong field used
    EMPTY_RESULT            = "empty_result"

    # Column or table does not exist in schema
    SCHEMA_MISMATCH         = "schema_mismatch"

    # MongoDB pipeline invalid — bad stage, wrong operator
    PIPELINE_ERROR          = "pipeline_error"

    # Data type mismatch — comparing string to int etc
    DATA_TYPE_ERROR         = "data_type_error"

    # Query timed out — too expensive, needs limit or index hint
    TIMEOUT                 = "timeout"

    # Contract violation — answer does not match expected format
    CONTRACT_VIOLATION      = "contract_violation"

    # Unknown error — catch-all for unclassified failures
    UNKNOWN                 = "unknown"


# ── error message patterns → failure type ────────────────────────────────────

ERROR_PATTERNS = [
    # SQL syntax errors
    (["syntax error", "parse error", "unexpected token",
      "invalid sql", "near \""], FailureType.QUERY_SYNTAX_ERROR),

    # Schema mismatches
    (["column", "does not exist", "no such column",
      "undefined column", "unknown column",
      "relation", "no such table", "table not found"],
     FailureType.SCHEMA_MISMATCH),

    # Data type errors
    (["invalid input syntax", "cannot cast",
      "data type mismatch", "operator does not exist",
      "integer out of range"], FailureType.DATA_TYPE_ERROR),

    # MongoDB pipeline errors
    (["unrecognized pipeline stage", "unknown operator",
      "invalid pipeline", "aggregate", "$match",
      "unknown top level operator"], FailureType.PIPELINE_ERROR),

    # Timeout
    (["timeout", "timed out", "exceeded",
      "query cancelled"], FailureType.TIMEOUT),

    # Join key issues — detected from empty results + cross-db queries
    (["businessid_", "businessref_", "prefix",
      "key mismatch", "foreign key"], FailureType.JOIN_KEY_MISMATCH),
]


def classify(error_message: str, db_type: str = "", row_count: int = -1) -> FailureType:
    """
    Classify a failure into a typed FailureType.

    Args:
        error_message: the error string from the database or MCP server
        db_type:       postgres, mongodb, sqlite, duckdb
        row_count:     -1 if not applicable, 0 for empty results

    Returns:
        FailureType enum value
    """
    if not error_message and row_count == 0:
        return FailureType.EMPTY_RESULT

    if not error_message:
        return FailureType.UNKNOWN

    msg_lower = error_message.lower()

    # check database type mismatch first
    if db_type == "mongodb" and any(
        kw in msg_lower for kw in ["syntax error", "select", "from", "where"]
    ):
        return FailureType.DATABASE_TYPE_ERROR

    if db_type in ("postgres", "sqlite", "duckdb") and any(
        kw in msg_lower for kw in ["pipeline", "aggregate", "$match"]
    ):
        return FailureType.DATABASE_TYPE_ERROR

    # match against error patterns
    for keywords, failure_type in ERROR_PATTERNS:
        if any(kw in msg_lower for kw in keywords):
            return failure_type

    return FailureType.UNKNOWN


def describe(failure_type: FailureType) -> str:
    """Return a human-readable description of a failure type."""
    descriptions = {
        FailureType.QUERY_SYNTAX_ERROR:  "SQL syntax error — wrong dialect or typo",
        FailureType.JOIN_KEY_MISMATCH:   "Join key format mismatch across databases",
        FailureType.DATABASE_TYPE_ERROR: "Wrong query format for this database type",
        FailureType.EMPTY_RESULT:        "Query returned no results — filters too strict",
        FailureType.SCHEMA_MISMATCH:     "Column or table does not exist in schema",
        FailureType.PIPELINE_ERROR:      "MongoDB aggregation pipeline invalid",
        FailureType.DATA_TYPE_ERROR:     "Data type mismatch in comparison or cast",
        FailureType.TIMEOUT:             "Query timed out — too expensive",
        FailureType.CONTRACT_VIOLATION:  "Answer format does not match expected",
        FailureType.UNKNOWN:             "Unclassified error",
    }
    return descriptions.get(failure_type, "Unknown failure")