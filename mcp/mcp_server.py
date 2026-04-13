"""
Oracle Forge — Unified MCP Server
Handles all four database types on a single port 5000.

Endpoints:
  GET  /v1/tools              — list all tools across all DB types
  POST /v1/tools/{tool_name}  — execute a tool
  GET  /schema/{tool_name}    — full schema for any database
  GET  /health                — server health + database status
  GET  /                      — root info
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from mcp.db_config import ALL_TOOLS, PG_TOOLS, MONGO_TOOLS, SQLITE_TOOLS, DUCKDB_TOOLS
import mcp.postgres_tools as pg
import mcp.mongo_tools    as mongo
import mcp.sqlite_tools   as sqlite
import mcp.duckdb_tools   as duck

# ── app setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Oracle Forge — Unified MCP Server",
    description="Single MCP server for PostgreSQL, MongoDB, SQLite and DuckDB",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── request models ────────────────────────────────────────────────────────────

class SQLRequest(BaseModel):
    sql: str

class PipelineRequest(BaseModel):
    pipeline: str

# ── routing helpers ───────────────────────────────────────────────────────────

def _get_db_type(tool_name: str) -> str:
    tool = ALL_TOOLS.get(tool_name)
    if tool is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. "
                   f"Available tools: {list(ALL_TOOLS.keys())}"
        )
    return tool["db_type"]


def _execute(tool_name: str, db_type: str, body: dict) -> dict:
    """Route the tool call to the correct handler."""
    if db_type == "postgres":
        sql = body.get("sql", "").strip()
        if not sql:
            raise HTTPException(status_code=400, detail="sql field is required.")
        return pg.execute_query(tool_name, sql)

    if db_type == "mongodb":
        pipeline = body.get("pipeline", "[]").strip()
        return mongo.execute_query(tool_name, pipeline)

    if db_type == "sqlite":
        sql = body.get("sql", "").strip()
        if not sql:
            raise HTTPException(status_code=400, detail="sql field is required.")
        return sqlite.execute_query(tool_name, sql)

    if db_type == "duckdb":
        sql = body.get("sql", "").strip()
        if not sql:
            raise HTTPException(status_code=400, detail="sql field is required.")
        return duck.execute_query(tool_name, sql)

    raise HTTPException(status_code=500, detail=f"Unknown db_type: {db_type}")

# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/v1/tools")
def get_tools():
    """
    List all available tools across all four database types.
    The agent calls this on startup to discover what tools exist.
    """
    all_tools = (
        pg.list_tools()    +
        mongo.list_tools() +
        sqlite.list_tools()+
        duck.list_tools()
    )
    return {
        "tools":       all_tools,
        "total_count": len(all_tools),
        "by_db_type": {
            "postgres": len(PG_TOOLS),
            "mongodb":  len(MONGO_TOOLS),
            "sqlite":   len(SQLITE_TOOLS),
            "duckdb":   len(DUCKDB_TOOLS),
        },
    }


@app.post("/v1/tools/{tool_name}")
async def invoke_tool(tool_name: str, body: dict):
    """
    Execute any tool by name.

    For PostgreSQL, SQLite, DuckDB:
      { "sql": "SELECT ..." }

    For MongoDB:
      { "pipeline": "[{\"$limit\": 5}]" }

    Returns structured result matching the same format across all DB types.
    Error details are in the response body not the HTTP status code
    so the agent self-correction loop can read and handle them.
    """
    db_type = _get_db_type(tool_name)
    result  = _execute(tool_name, db_type, body)
    return result


@app.get("/schema/{tool_name}")
def get_schema(tool_name: str):
    """
    Return the full schema of the database mapped to tool_name.
    Used by utils/schema_introspector.py to populate AGENT.md and KB files.
    """
    db_type = _get_db_type(tool_name)

    if db_type == "postgres":
        result = pg.get_schema(tool_name)
    elif db_type == "mongodb":
        result = mongo.get_schema(tool_name)
    elif db_type == "sqlite":
        result = sqlite.get_schema(tool_name)
    elif db_type == "duckdb":
        result = duck.get_schema(tool_name)
    else:
        raise HTTPException(status_code=500, detail=f"Unknown db_type: {db_type}")

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.get("/health")
def health():
    """
    Server health check.
    Checks PostgreSQL connectivity, MongoDB connectivity,
    and existence of all SQLite and DuckDB files.
    """
    status = {}

    # PostgreSQL
    try:
        import psycopg2
        from mcp.db_config import PG_CONFIG
        conn = psycopg2.connect(
            host=PG_CONFIG["host"],
            port=PG_CONFIG["port"],
            user=PG_CONFIG["user"],
            password=PG_CONFIG["password"],
            dbname="postgres",
            connect_timeout=3,
        )
        conn.close()
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = f"error: {e}"

    # MongoDB
    try:
        from pymongo import MongoClient
        from mcp.db_config import MONGO_CONFIG
        client = MongoClient(MONGO_CONFIG["uri"], serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        client.close()
        status["mongodb"] = "ok"
    except Exception as e:
        status["mongodb"] = f"error: {e}"

    # SQLite files
    sqlite_status = {}
    for name, cfg in SQLITE_TOOLS.items():
        sqlite_status[name] = "ok" if Path(cfg["path"]).exists() else "file missing"
    status["sqlite"] = sqlite_status

    # DuckDB files
    duckdb_status = {}
    for name, cfg in DUCKDB_TOOLS.items():
        duckdb_status[name] = "ok" if Path(cfg["path"]).exists() else "file missing"
    status["duckdb"] = duckdb_status

    overall = (
        status["postgres"] == "ok" and
        status["mongodb"]  == "ok" and
        all(v == "ok" for v in sqlite_status.values()) and
        all(v == "ok" for v in duckdb_status.values())
    )

    return {
        "status":   "ok" if overall else "degraded",
        "server":   "oracle-forge-mcp",
        "port":     5000,
        "details":  status,
    }


@app.get("/")
def root():
    """Root endpoint — confirms server is running."""
    return {
        "server":      "Oracle Forge Unified MCP Server",
        "version":     "1.0.0",
        "port":        5000,
        "total_tools": len(ALL_TOOLS),
        "by_db_type": {
            "postgres": len(PG_TOOLS),
            "mongodb":  len(MONGO_TOOLS),
            "sqlite":   len(SQLITE_TOOLS),
            "duckdb":   len(DUCKDB_TOOLS),
        },
        "docs": "http://127.0.0.1:5000/docs",
    }


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "5000"))
    print(f"Starting Oracle Forge Unified MCP Server on port {port}")
    print(f"Total tools: {len(ALL_TOOLS)}")
    print(f"  PostgreSQL: {len(PG_TOOLS)} tools")
    print(f"  MongoDB:    {len(MONGO_TOOLS)} tools")
    print(f"  SQLite:     {len(SQLITE_TOOLS)} tools")
    print(f"  DuckDB:     {len(DUCKDB_TOOLS)} tools")
    uvicorn.run(
        "mcp.mcp_server:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="info",
    )