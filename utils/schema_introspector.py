"""
Schema Introspector
Connects to the MCP server, reads the schema of every database,
samples real data, calls Claude to enrich the schema with domain context,
and writes structured markdown files into kb/domain/.

Run once before building AGENT.md and the conductor agent.

Usage:
    cd /home/project/oracle-forge
    source .env
    python -m utils.schema_introspector
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from openai import OpenAI

# ── config ────────────────────────────────────────────────────────────────────

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

MCP_URL     = os.getenv("MCP_URL",  "http://127.0.0.1:5000")
KB_DIR      = Path(__file__).parent.parent / "kb" / "domain"
ORACLE_ROOT = Path(__file__).parent.parent

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL   = "anthropic/claude-sonnet-4.6"

# dataset name → kb domain file mapping
DATASET_MAP = {
    "yelp":            ["query_mongo_yelp_business", "query_mongo_yelp_checkin",  "query_duckdb_yelp_user"],
    "agnews":          ["query_mongo_agnews",         "query_sqlite_agnews_metadata"],
    "bookreview":      ["query_postgres_bookreview",  "query_sqlite_bookreview"],
    "crmarenapro":     ["query_postgres_crmarenapro", "query_sqlite_crmarenapro_core",
                        "query_sqlite_crmarenapro_products", "query_sqlite_crmarenapro_territory",
                        "query_duckdb_crmarenapro_activities", "query_duckdb_crmarenapro_sales"],
    "deps_dev":        ["query_sqlite_deps_dev_package", "query_duckdb_deps_dev_project"],
    "github_repos":    ["query_sqlite_github_metadata", "query_duckdb_github_artifacts"],
    "googlelocal":     ["query_postgres_googlelocal", "query_sqlite_googlelocal_review"],
    "music_brainz":    ["query_sqlite_music_brainz",  "query_duckdb_music_brainz_sales"],
    "pancancer":       ["query_postgres_pancancer",   "query_duckdb_pancancer_molecular"],
    "patents":         ["query_postgres_patents",     "query_sqlite_patents"],
    "stockindex":      ["query_sqlite_stockindex_info", "query_duckdb_stockindex_trade"],
    "stockmarket":     ["query_sqlite_stockmarket_info", "query_duckdb_stockmarket_trade"],
}

# ── MCP helpers ───────────────────────────────────────────────────────────────

def get_schema(tool_name: str) -> dict:
    """Fetch schema from MCP /schema endpoint."""
    # skip schema for stockmarket_trade — 2754 tables causes timeout
    SKIP_SCHEMA = {"query_duckdb_stockmarket_trade"}

    try:
        r = requests.get(f"{MCP_URL}/schema/{tool_name}", timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [ERROR] schema fetch failed for {tool_name}: {e}")
        return {}


def get_sample(tool_name: str, db_type: str) -> list:
    """Fetch 3 sample rows from MCP /v1/tools endpoint."""
    try:
        if db_type == "mongodb":
            payload = {"pipeline": '[{"$limit": 3}]'}
        else:
            payload = {"sql": "SELECT * FROM (SELECT * FROM information_schema.tables LIMIT 1) t"}

        # for SQL databases get actual table data
        if db_type in ("postgres", "sqlite", "duckdb"):
            schema = get_schema(tool_name)
            tables = list(schema.get("schema", {}).keys())
            if tables:
                tbl = tables[0]
                if db_type == "postgres":
                    payload = {"sql": f'SELECT * FROM "{tbl}" LIMIT 3'}
                else:
                    payload = {"sql": f"SELECT * FROM {tbl} LIMIT 3"}

        r = requests.post(
            f"{MCP_URL}/v1/tools/{tool_name}",
            json=payload,
            timeout=30
        )
        r.raise_for_status()
        data = r.json()
        return data.get("result", [])[:3]
    except Exception as e:
        print(f"  [WARN] sample fetch failed for {tool_name}: {e}")
        return []


# ── LLM enrichment ────────────────────────────────────────────────────────────

def enrich_with_claude(dataset: str, tool_schemas: list[dict]) -> str:
    """
    Call Claude to enrich raw schema with domain context.
    Returns markdown string ready to write to kb/domain/.
    """
    if not OPENROUTER_KEY:
        print("  [WARN] No API key found. Writing raw schema without enrichment.")
        return _raw_markdown(dataset, tool_schemas)

    client = OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge Schema Introspector",
        }
    )

    schema_text = json.dumps(tool_schemas, indent=2)

    prompt = f"""You are writing a Knowledge Base document for an AI data agent.
The agent will use this document to answer business questions against the {dataset} dataset.

Below is the raw schema and sample data extracted from the {dataset} databases.
Write a structured markdown document (maximum 400 words) that covers:

1. Dataset overview — what this dataset is about in one sentence
2. For each database/table/collection:
   - What it contains in plain English
   - Key fields and what they mean
   - Data types and value ranges where relevant
   - Any important relationships between tables
3. Join keys — how tables/collections link to each other, including any format differences
4. Domain terms — any business terms specific to this dataset
5. Known query patterns — what kinds of questions this dataset can answer

Be specific and precise. Remove anything the LLM already knows from pretraining.
Only include what is specific to THIS dataset's structure and quirks.

RAW SCHEMA AND SAMPLES:
{schema_text}

Write only the markdown document. No preamble or explanation."""

    try:
        response = client.chat.completions.create(
            model=CLAUDE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"  [ERROR] Claude enrichment failed: {e}")
        return _raw_markdown(dataset, tool_schemas)


def _raw_markdown(dataset: str, tool_schemas: list[dict]) -> str:
    """Fallback — write raw schema as markdown without enrichment."""
    lines = [f"# {dataset} — Database Schema\n"]
    for ts in tool_schemas:
        lines.append(f"## {ts['tool_name']} ({ts['db_type']})\n")
        for tbl, cols in ts.get("schema", {}).items():
            lines.append(f"### {tbl}\n")
            for col in cols:
                if isinstance(col, dict):
                    name = col.get("column") or col.get("field", "")
                    dtype = col.get("type", "")
                    lines.append(f"- `{name}`: {dtype}")
                else:
                    lines.append(f"- {col}")
            lines.append("")
    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────

def introspect_all():
    """
    Main entry point.
    Loops through all datasets, fetches schemas and samples,
    enriches with Claude, writes to kb/domain/.
    """
    KB_DIR.mkdir(parents=True, exist_ok=True)
    changelog = KB_DIR / "CHANGELOG.md"

    # verify MCP server is running
    try:
        r = requests.get(f"{MCP_URL}/health", timeout=5)
        health = r.json()
        print(f"MCP server: {health['status']} — {health['details']['postgres']}")
    except Exception as e:
        print(f"[ERROR] MCP server not reachable at {MCP_URL}: {e}")
        print("Start it with: python -m mcp.mcp_server")
        sys.exit(1)

    # get all tools from MCP
    tools_response = requests.get(f"{MCP_URL}/v1/tools").json()
    all_tools       = {t["name"]: t for t in tools_response["tools"]}
    print(f"Found {len(all_tools)} tools across all databases\n")

    changelog_entries = []

    for dataset, tool_names in DATASET_MAP.items():
        print(f"Processing dataset: {dataset}")
        tool_schemas = []

        for tool_name in tool_names:
            if tool_name not in all_tools:
                print(f"  [SKIP] {tool_name} not found in MCP tools")
                continue

            db_type = all_tools[tool_name]["db_type"]
            print(f"  Fetching schema: {tool_name} ({db_type})")

            schema = get_schema(tool_name)
            if not schema or schema.get("error"):
                print(f"  [SKIP] schema error for {tool_name}")
                continue

            print(f"  Fetching sample: {tool_name}")
            sample = get_sample(tool_name, db_type)

            tool_schemas.append({
                "tool_name": tool_name,
                "db_type":   db_type,
                "schema":    schema.get("schema", {}),
                "sample":    sample,
            })
            time.sleep(0.5)  # rate limit protection

        if not tool_schemas:
            print(f"  [SKIP] no schemas found for {dataset}\n")
            continue

        print(f"  Enriching with Claude...")
        markdown = enrich_with_claude(dataset, tool_schemas)

        # write to kb/domain/
        out_path = KB_DIR / f"dab_{dataset}.md"
        out_path.write_text(markdown, encoding="utf-8")
        print(f"  Written: {out_path}")

        changelog_entries.append(f"- `dab_{dataset}.md` — generated from {len(tool_schemas)} tools")
        print()

    # write CHANGELOG
    from datetime import datetime
    changelog_text = f"# KB Domain Changelog\n\n## {datetime.now().strftime('%Y-%m-%d')}\n\n"
    changelog_text += "Schema introspector run — all domain files generated.\n\n"
    changelog_text += "\n".join(changelog_entries)
    changelog_text += "\n\nEach document was enriched with Claude and requires injection testing before use.\n"
    changelog.write_text(changelog_text, encoding="utf-8")

    print(f"\nDone. {len(changelog_entries)} domain files written to {KB_DIR}")
    print(f"Next step: review each file in kb/domain/ and run injection tests.")


if __name__ == "__main__":
    introspect_all()