"""
Recovery Router
Maps each FailureType to a specific recovery strategy.
Called by sub-agents when a query fails to get a targeted fix prompt
rather than a generic retry.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from agent.self_correction.failure_types import FailureType, classify, describe

load_dotenv(Path(__file__).parent.parent.parent / ".env")

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL   = "anthropic/claude-3-5-haiku"  # Haiku: fast SQL fixing, no need for Sonnet


def get_client() -> OpenAI:
    return OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge Recovery Router",
        }
    )


def recover(
    failed_query: str,
    error:        str,
    db_type:      str,
    tool_name:    str,
    schema:       dict,
    context:      str = "",
    row_count:    int = -1,
) -> dict:
    """
    Given a failed query, classify the failure and apply a targeted fix.

    Args:
        failed_query: the SQL or MongoDB pipeline that failed
        error:        error message from MCP server
        db_type:      postgres, mongodb, sqlite, duckdb
        tool_name:    MCP tool that was called
        schema:       database schema dict
        context:      AGENT.md + KB domain content
        row_count:    row count if query succeeded but returned wrong results

    Returns:
        dict with:
          - fixed_query: corrected SQL or pipeline
          - failure_type: classified failure type name
          - explanation: what was wrong and how it was fixed
          - confidence: high/medium/low
    """
    failure_type = classify(error, db_type, row_count)
    strategy     = _get_strategy(failure_type, db_type)

    fixed_query, explanation = _apply_fix(
        failed_query, error, db_type, tool_name,
        schema, context, failure_type, strategy
    )

    return {
        "fixed_query":   fixed_query,
        "failure_type":  failure_type.value,
        "description":   describe(failure_type),
        "explanation":   explanation,
        "strategy":      strategy,
        "confidence":    _estimate_confidence(failure_type, fixed_query),
    }


# ── recovery strategies ───────────────────────────────────────────────────────

def _get_strategy(failure_type: FailureType, db_type: str) -> str:
    """Return a targeted fix instruction for each failure type."""

    strategies = {
        FailureType.QUERY_SYNTAX_ERROR: (
            "Fix the SQL syntax error. "
            "Check: correct dialect for this DB type, "
            "proper quoting of identifiers, valid function names. "
            f"This is a {db_type} database."
        ),
        FailureType.JOIN_KEY_MISMATCH: (
            "Fix the join key format mismatch. "
            "In the yelp dataset: MongoDB uses 'businessid_##' prefix, "
            "DuckDB uses 'businessref_##' prefix. "
            "Replace the prefix when joining across databases. "
            "Use string replacement or REPLACE() function."
        ),
        FailureType.DATABASE_TYPE_ERROR: (
            f"This is a {db_type} database. "
            "For MongoDB: use aggregation pipeline JSON array. "
            "For PostgreSQL/SQLite/DuckDB: use SQL SELECT statement. "
            "Rewrite the query in the correct format for this database type."
        ),
        FailureType.EMPTY_RESULT: (
            "The query returned no results. Check: "
            "1. Field names — verify against schema "
            "2. Filter values — may use abbreviations (IN not Indiana) "
            "3. Case sensitivity — add case-insensitive matching "
            "4. Join keys — verify prefix format matches "
            "Relax the filters or fix the field names."
        ),
        FailureType.SCHEMA_MISMATCH: (
            "A column or table does not exist. "
            "Check the schema carefully and use only existing column names. "
            "For PostgreSQL: wrap mixed-case names in double quotes. "
            "Verify the exact table and column names from the schema."
        ),
        FailureType.PIPELINE_ERROR: (
            "Fix the MongoDB aggregation pipeline. "
            "Ensure it is a valid JSON array of stage objects. "
            "Valid stages: $match, $group, $project, $sort, $limit, $unwind, $lookup. "
            "Check operator names start with $ and field names are correct."
        ),
        FailureType.DATA_TYPE_ERROR: (
            "Fix the data type mismatch. "
            "Use CAST() or :: for type conversion. "
            "Check that you are comparing compatible types. "
            "Numeric fields should not be compared to strings without casting."
        ),
        FailureType.TIMEOUT: (
            "The query is too expensive. "
            "Add LIMIT clause to reduce result set. "
            "Avoid SELECT * on large tables — select only needed columns. "
            "Add WHERE clause to filter early."
        ),
        FailureType.UNKNOWN: (
            "An unexpected error occurred. "
            "Carefully rewrite the query from scratch "
            "using only the schema provided."
        ),
    }

    return strategies.get(failure_type, strategies[FailureType.UNKNOWN])


def _apply_fix(
    failed_query:  str,
    error:         str,
    db_type:       str,
    tool_name:     str,
    schema:        dict,
    context:       str,
    failure_type:  FailureType,
    strategy:      str,
) -> tuple[str, str]:
    """Call Claude to apply the targeted fix strategy."""

    messages = [
        {
            "role": "system",
            "content": f"""You are a database query debugger specializing in {db_type}.

FAILURE TYPE: {failure_type.value} — {describe(failure_type)}

FIX STRATEGY:
{strategy}

SCHEMA:
{json.dumps(schema, indent=2)}

{context}

Respond with JSON only:
{{
  "fixed_query": "the corrected query here",
  "explanation": "one sentence: what was wrong and what you changed"
}}

For SQL databases: fixed_query must be a SQL SELECT statement.
For MongoDB: fixed_query must be a valid JSON array string of pipeline stages."""
        },
        {
            "role": "user",
            "content": f"Failed query:\n{failed_query}\n\nError:\n{error}\n\nApply the fix:"
        }
    ]

    try:
        client   = get_client()
        response = client.chat.completions.create(
            model=CLAUDE_MODEL,
            messages=messages,
            max_tokens=600,
            temperature=0.0,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result      = json.loads(content.strip())
        fixed_query = result.get("fixed_query", "")
        explanation = result.get("explanation", "")
        return fixed_query, explanation
    except Exception as e:
        return "", f"Recovery failed: {e}"


def _estimate_confidence(failure_type: FailureType, fixed_query: str) -> str:
    """Estimate confidence in the fix."""
    if not fixed_query:
        return "low"
    if failure_type in (FailureType.QUERY_SYNTAX_ERROR,
                        FailureType.SCHEMA_MISMATCH,
                        FailureType.JOIN_KEY_MISMATCH):
        return "high"
    if failure_type in (FailureType.EMPTY_RESULT,
                        FailureType.DATA_TYPE_ERROR):
        return "medium"
    return "low"