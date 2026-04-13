"""
Multi-Pass Retrieval
Retries a database query with progressively broader context when
the first attempt returns empty or insufficient results.

Three pass levels:
  Pass 1 — exact query as planned
  Pass 2 — relaxed filters (case-insensitive, broader date ranges)
  Pass 3 — minimal query (just get schema/sample to understand the data)

Used by sub-agents when a query returns 0 rows but no error.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

MCP_URL        = os.getenv("MCP_URL", "http://127.0.0.1:5000")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL   = "anthropic/claude-sonnet-4.6"


def get_client() -> OpenAI:
    return OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge Multi-Pass Retrieval",
        }
    )


def retrieve(
    tool_name:  str,
    query:      str,
    db_type:    str,
    task:       str,
    schema:     dict,
    context:    str = "",
    max_passes: int = 3,
) -> dict:
    """
    Execute a query with multi-pass fallback strategy.
    If pass N returns empty results, generate a broader pass N+1.

    Args:
        tool_name:  MCP tool name
        query:      initial SQL or MongoDB pipeline
        db_type:    postgres, mongodb, sqlite, duckdb
        task:       plain English description of what to find
        schema:     database schema
        context:    AGENT.md + KB domain content
        max_passes: maximum number of passes (default 3)

    Returns:
        best result found across all passes, with pass metadata
    """
    passes      = []
    best_result = None

    current_query = query

    for pass_num in range(1, max_passes + 1):
        result = _execute(tool_name, current_query, db_type)
        result["pass_num"] = pass_num
        result["query"]    = current_query
        passes.append(result)

        # if we got results, use them
        if result.get("row_count", 0) > 0 and not result.get("error"):
            best_result = result
            break

        # if this was the last pass, stop
        if pass_num >= max_passes:
            break

        # generate a broader query for the next pass
        current_query = _broaden_query(
            current_query, db_type, task, schema, context,
            pass_num, result.get("error", "")
        )
        if not current_query:
            break

    # if no pass succeeded return the last result
    if best_result is None:
        best_result = passes[-1] if passes else {}

    best_result["passes"]     = passes
    best_result["total_passes"] = len(passes)
    return best_result


def _execute(tool_name: str, query: str, db_type: str) -> dict:
    """Execute a single query via MCP."""
    try:
        payload = {"pipeline": query} if db_type == "mongodb" else {"sql": query}
        r = requests.post(
            f"{MCP_URL}/v1/tools/{tool_name}",
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "result":         [],
            "query_used":     query,
            "db_type":        db_type,
            "tool_name":      tool_name,
            "row_count":      0,
            "execution_time": 0,
            "error":          str(e),
        }


def _broaden_query(
    query:    str,
    db_type:  str,
    task:     str,
    schema:   dict,
    context:  str,
    pass_num: int,
    error:    str,
) -> str:
    """Ask Claude to generate a broader query for the next pass."""

    pass_instructions = {
        1: (
            "The previous query returned no results. "
            "Relax the filters: use case-insensitive matching, "
            "remove strict equality checks, use LIKE or regex instead. "
            "Keep the core intent but broaden the search."
        ),
        2: (
            "The previous query still returned no results. "
            "Write a minimal diagnostic query: "
            "just SELECT a few columns with LIMIT 5, no filters. "
            "The goal is to understand what data is actually in the table."
        ),
    }

    instruction = pass_instructions.get(pass_num, pass_instructions[2])

    messages = [
        {
            "role": "system",
            "content": f"""You are a database query optimizer.

PASS {pass_num + 1} STRATEGY:
{instruction}

SCHEMA:
{json.dumps(schema, indent=2)}

{context}

Return only the query. No explanation, no markdown."""
        },
        {
            "role": "user",
            "content": (
                f"Task: {task}\n"
                f"Previous query (returned 0 rows):\n{query}\n"
                f"Error (if any): {error}\n\n"
                f"Write a broader Pass {pass_num + 1} query:"
            )
        }
    ]

    try:
        client   = get_client()
        response = client.chat.completions.create(
            model=CLAUDE_MODEL,
            messages=messages,
            max_tokens=400,
            temperature=0.0,
        )
        q = response.choices[0].message.content.strip()
        if q.startswith("```"):
            q = q.split("```")[1]
            if q.startswith(("sql", "json")):
                q = q[3:] if q.startswith("sql") else q[4:]
        return q.strip()
    except Exception:
        return ""