"""
SQLite Sub-Agent
Specialist agent for SQLite databases.
Handles file-based SQLite queries with standard SQL dialect.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from agent.self_correction.recovery_router import recover

load_dotenv(Path(__file__).parent.parent.parent / ".env")

MCP_URL        = os.getenv("MCP_URL", "http://127.0.0.1:5000")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL   = "anthropic/claude-sonnet-4.6"


def get_client() -> OpenAI:
    return OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge SQLite Agent",
        }
    )


def run(
    tool_name:     str,
    task:          str,
    context:       str = "",
    prior_results: list[dict] = None,
    max_retries:   int = 2,
) -> dict:
    prior_results = prior_results or []
    schema        = _get_schema(tool_name)
    sql           = _generate_query(tool_name, task, context, schema, prior_results)

    if not sql:
        return _error_result(tool_name, task, "Failed to generate SQL query")

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
                db_type="sqlite",  
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
    tool_name:     str,
    task:          str,
    context:       str,
    schema:        dict,
    prior_results: list[dict],
) -> str:
    prior_text = ""
    if prior_results:
        prior_text = "\n\nPRIOR RESULTS FROM OTHER DATABASES:\n"
        for pr in prior_results:
            prior_text += f"- {pr.get('tool_name', '')}: {json.dumps(pr.get('result', [])[:5], indent=2)}\n"

    messages = [
        {
            "role": "system",
            "content": f"""You are a SQLite expert. Write a precise SQL SELECT query.

RULES:
- Standard SQL only — no PostgreSQL-specific syntax
- Use only SELECT statements
- Return only the SQL query, nothing else
- No markdown, no explanation, no backticks
- SQLite does not support RIGHT JOIN or FULL OUTER JOIN
- Use CAST() for type conversions

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
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.startswith("sql"):
                sql = sql[3:]
        return sql.strip()
    except Exception:
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
            "db_type":        "sqlite",
            "tool_name":      tool_name,
            "row_count":      0,
            "execution_time": 0,
            "error":          str(e),
        }


def _error_result(tool_name: str, task: str, msg: str) -> dict:
    return {
        "result":         [],
        "query_used":     "",
        "db_type":        "sqlite",
        "tool_name":      tool_name,
        "task":           task,
        "row_count":      0,
        "execution_time": 0,
        "error":          msg,
    }