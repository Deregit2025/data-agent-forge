"""
MongoDB Sub-Agent
Specialist agent for MongoDB databases.
Generates aggregation pipelines and handles document-oriented queries.
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
CLAUDE_MODEL   = "anthropic/claude-3-5-haiku"  # Haiku: fast query generation


def get_client() -> OpenAI:
    return OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge MongoDB Agent",
        }
    )


def run(
    tool_name:     str,
    task:          str,
    context:       str = "",
    prior_results: list[dict] = None,
    max_retries:   int = 2,
) -> dict:
    """
    Execute a MongoDB task.

    Args:
        tool_name:     MCP tool to use (e.g. query_mongo_yelp_business)
        task:          plain English description of what to find
        context:       AGENT.md + KB domain content
        prior_results: results from previous sub-agent calls
        max_retries:   max self-correction attempts
    """
    prior_results = prior_results or []
    schema        = _get_schema(tool_name)
    pipeline      = _generate_pipeline(tool_name, task, context, schema, prior_results)

    if not pipeline:
        return _error_result(tool_name, task, "Failed to generate MongoDB pipeline")

    for attempt in range(max_retries + 1):
        result = _execute(tool_name, pipeline)

        if not result.get("error"):
            result["task"]    = task
            result["attempt"] = attempt
            return result

        if attempt < max_retries:
            fix = recover(
                failed_query=pipeline,
                error=result["error"],
                db_type="mongodb",
                tool_name=tool_name,
                schema=schema,
                context=context,
            )
            pipeline = fix.get("fixed_query", "")
            if not pipeline:
                break


    result["task"] = task
    return result


def _get_schema(tool_name: str) -> dict:
    try:
        r = requests.get(f"{MCP_URL}/schema/{tool_name}", timeout=30)
        data = r.json()
        return data.get("schema", {})
    except Exception:
        return {}


def _generate_pipeline(
    tool_name:     str,
    task:          str,
    context:       str,
    schema:        dict,
    prior_results: list[dict],
) -> str:
    prior_text = ""
    if prior_results:
        prior_text = "\n\nPRIOR RESULTS FROM OTHER DATABASES (use for cross-database joins):\n"
        for pr in prior_results:
            tool    = pr.get("tool_name", "")
            rows    = pr.get("result", [])
            n_total = pr.get("row_count", len(rows))

            # extract all ID/ref values — never truncate
            id_fields = ["business_ref", "business_id", "user_id", "book_id",
                         "gmap_id", "_id", "repo_id", "package_name", "patent_id"]
            extracted = {}
            for field in id_fields:
                vals = [r[field] for r in rows if field in r]
                if vals:
                    extracted[field] = vals

            if extracted:
                prior_text += f"\n- {tool} ({n_total} rows total):\n"
                for field, vals in extracted.items():
                    # convert businessref_## → businessid_## for MongoDB $in
                    if field == "business_ref":
                        converted = [v.replace("businessref_", "businessid_") for v in vals]
                        prior_text += f"  All business_id values for $in ({len(converted)}): {converted}\n"
                    else:
                        prior_text += f"  All {field} values ({len(vals)}): {vals}\n"
                prior_text += f"  Sample rows: {json.dumps(rows[:3], indent=2)}\n"
            else:
                prior_text += f"\n- {tool} ({n_total} rows): {json.dumps(rows[:50], indent=2)}\n"

    messages = [
        {
            "role": "system",
            "content": f"""You are a MongoDB aggregation pipeline expert.

RULES:
- Return ONLY a valid JSON array of pipeline stages
- Use $match, $group, $project, $sort, $limit, $count, $unwind as needed
- No markdown, no explanation, no backticks
- The pipeline must be parseable by json.loads()
- For location filtering: use {{"$regex": "in City, ST", "$options": "i"}} on description field
- For intersections: use {{"$match": {{"business_id": {{"$in": [...]}}}}}} with ALL IDs from prior results
- Do NOT use $out or $merge stages
- For counting: use [{{"$match": ...}}, {{"$count": "total"}}] — returns single row with count


SCHEMA (inferred from samples):
{json.dumps(schema, indent=2)}

{context}
{prior_text}"""
        },
        {
            "role": "user",
            "content": f"Tool: {tool_name}\nTask: {task}\n\nWrite the MongoDB aggregation pipeline:"
        }
    ]

    try:
        client   = get_client()
        response = client.chat.completions.create(
            model=CLAUDE_MODEL,
            messages=messages,
            max_tokens=800,
            temperature=0.0,
        )
        pipeline = response.choices[0].message.content.strip()
        if "```" in pipeline:
            parts = pipeline.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("["):
                    pipeline = part
                    break
        pipeline = pipeline.strip()
        json.loads(pipeline)
        return pipeline
    except Exception as e:
        return ""


def _execute(tool_name: str, pipeline: str) -> dict:
    try:
        r = requests.post(
            f"{MCP_URL}/v1/tools/{tool_name}",
            json={"pipeline": pipeline},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "result":         [],
            "query_used":     pipeline,
            "db_type":        "mongodb",
            "tool_name":      tool_name,
            "row_count":      0,
            "execution_time": 0,
            "error":          str(e),
        }


def _error_result(tool_name: str, task: str, msg: str) -> dict:
    return {
        "result":         [],
        "query_used":     "",
        "db_type":        "mongodb",
        "tool_name":      tool_name,
        "task":           task,
        "row_count":      0,
        "execution_time": 0,
        "error":          msg,
    }