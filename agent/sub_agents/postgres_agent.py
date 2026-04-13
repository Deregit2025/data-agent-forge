"""
PostgreSQL Sub-Agent
Specialist agent for PostgreSQL databases.
Receives a task from the conductor, generates a SQL query,
calls the MCP server, and returns a structured result.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

MCP_URL        = os.getenv("MCP_URL", "http://127.0.0.1:5000")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL   = "anthropic/claude-haiku-4.5-20251001"  # Haiku: fast SQL generation

from agent.self_correction.recovery_router import recover
from openai import OpenAI


def get_client() -> OpenAI:
    return OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge PostgreSQL Agent",
        }
    )


def run(
    tool_name:   str,
    task:        str,
    context:     str = "",
    prior_results: list[dict] = None,
    max_retries: int = 2,
) -> dict:
    """
    Execute a PostgreSQL task.

    Args:
        tool_name:     MCP tool to use (e.g. query_postgres_bookreview)
        task:          plain English description of what to find
        context:       AGENT.md + KB domain content
        prior_results: results from previous sub-agent calls for cross-DB joins
        max_retries:   max self-correction attempts

    Returns:
        structured result dict
    """
    prior_results = prior_results or []

    # get schema for this tool
    schema = _get_schema(tool_name)

    # generate SQL query
    sql = _generate_query(tool_name, task, context, schema, prior_results)
    if not sql:
        return _error_result(tool_name, task, "Failed to generate SQL query")

    # execute with retries
    for attempt in range(max_retries + 1):
        result = _execute(tool_name, sql)

        if not result.get("error"):
            result["task"]    = task
            result["attempt"] = attempt
            return result

        if attempt < max_retries:
            fix = recover(
                failed_query=sql,
                error=result["error"],
                db_type="postgres",   # change to mongodb, sqlite, or duckdb per file
                tool_name=tool_name,
                schema=schema,
                context=context,
             )
            sql = fix.get("fixed_query", "")
            if not sql:
                 break

    result["task"] = task
    return result


def _get_schema(tool_name: str) -> dict:
    try:
        r = requests.get(f"{MCP_URL}/schema/{tool_name}", timeout=30)
        return r.json().get("schema", {})
    except Exception:
        return {}


def _generate_query(
    tool_name: str,
    task: str,
    context: str,
    schema: dict,
    prior_results: list[dict],
) -> str:
    prior_text = ""
    if prior_results:
        prior_text = "\n\nPRIOR RESULTS FROM OTHER DATABASES (use for cross-database joins):\n"
        for pr in prior_results:
            tool    = pr.get("tool_name", "")
            rows    = pr.get("result", [])
            n_total = pr.get("row_count", len(rows))

            # Extract every ID value so the IN clause is complete — never truncate IDs
            id_fields = ["business_id", "user_id", "book_id", "gmap_id", "_id",
                         "repo_id", "package_name", "patent_id", "ParticipantBarcode",
                         "article_id", "track_id", "Id", "id"]
            extracted = {}
            for field in id_fields:
                vals = [r[field] for r in rows if field in r]
                if vals:
                    extracted[field] = vals

            if extracted:
                prior_text += f"\n- {tool} ({n_total} rows total):\n"
                for field, vals in extracted.items():
                    prior_text += f"  All {field} values ({len(vals)}): {vals}\n"
                prior_text += f"  Sample rows: {json.dumps(rows[:3], indent=2)}\n"
            else:
                prior_text += f"\n- {tool} ({n_total} rows): {json.dumps(rows[:50], indent=2)}\n"

    messages = [
        {
            "role": "system",
            "content": f"""You are a PostgreSQL expert. Write a precise SQL SELECT query.

RULES:
- Always wrap mixed-case column and table names in double quotes
- Use only SELECT statements — no INSERT, UPDATE, DELETE
- Return only the SQL query, nothing else
- No markdown, no explanation, no backticks

SCHEMA:
{json.dumps(schema, indent=2)}

{context}
{prior_text}"""
        },
        {
            "role": "user",
            "content": f"Tool: {tool_name}\nTask: {task}\n\nWrite the SQL query:"
        }
    ]

    try:
        client   = get_client()
        response = client.chat.completions.create(
            model=CLAUDE_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.0,
        )
        sql = response.choices[0].message.content.strip()
        # clean any accidental markdown
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.startswith("sql"):
                sql = sql[3:]
        return sql.strip()
    except Exception as e:
        return ""

def _execute(tool_name: str, sql: str) -> dict:
    try:
        r = requests.post(
            f"{MCP_URL}/v1/tools/{tool_name}",
            json={"sql": sql},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "result":         [],
            "query_used":     sql,
            "db_type":        "postgres",
            "tool_name":      tool_name,
            "row_count":      0,
            "execution_time": 0,
            "error":          str(e),
        }


def _error_result(tool_name: str, task: str, msg: str) -> dict:
    return {
        "result":         [],
        "query_used":     "",
        "db_type":        "postgres",
        "tool_name":      tool_name,
        "task":           task,
        "row_count":      0,
        "execution_time": 0,
        "error":          msg,
    }