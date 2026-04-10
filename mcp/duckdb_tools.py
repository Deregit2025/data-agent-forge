import time
import duckdb
from typing import Any
from mcp.db_config import DUCKDB_TOOLS


def execute_query(tool_name: str, sql: str) -> dict[str, Any]:
    """
    Execute a read-only SQL query against the DuckDB file
    mapped to tool_name.

    Returns the same structured response as all other tool files.
    """
    tool = DUCKDB_TOOLS.get(tool_name)
    if tool is None:
        return _error_response(tool_name, sql, f"Unknown tool: '{tool_name}'")

    if not _is_read_only(sql):
        return _error_response(
            tool_name, sql,
            "Write operations are not permitted. Only SELECT queries are allowed."
        )

    db_path = tool["path"]
    if not db_path.exists():
        return _error_response(
            tool_name, sql,
            f"DuckDB file not found at {db_path}. "
            "Check DAB_PATH is set correctly."
        )

    start = time.perf_counter()
    try:
        conn     = duckdb.connect(str(db_path), read_only=True)
        relation = conn.execute(sql)
        cols     = [d[0] for d in relation.description]
        rows     = relation.fetchall()
        conn.close()

        elapsed = round(time.perf_counter() - start, 4)
        result  = [dict(zip(cols, row)) for row in rows]

        return {
            "result":         result,
            "query_used":     sql,
            "db_type":        "duckdb",
            "tool_name":      tool_name,
            "db_path":        str(db_path),
            "row_count":      len(result),
            "execution_time": elapsed,
            "error":          None,
        }

    except duckdb.Error as e:
        elapsed = round(time.perf_counter() - start, 4)
        return {
            "result":         [],
            "query_used":     sql,
            "db_type":        "duckdb",
            "tool_name":      tool_name,
            "db_path":        str(db_path),
            "row_count":      0,
            "execution_time": elapsed,
            "error":          str(e),
        }


def get_schema(tool_name: str) -> dict[str, Any]:
    """
    Return the full schema of the DuckDB database mapped to tool_name.
    Used by utils/schema_introspector.py to populate AGENT.md and KB files.
    """
    tool = DUCKDB_TOOLS.get(tool_name)
    if tool is None:
        return _error_response(tool_name, "", f"Unknown tool: '{tool_name}'")

    db_path = tool["path"]
    if not db_path.exists():
        return _error_response(
            tool_name, "",
            f"DuckDB file not found at {db_path}."
        )

    try:
        conn   = duckdb.connect(str(db_path), read_only=True)
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main'"
        ).fetchall()

        schema = {}
        for (tbl,) in tables:
            cols = conn.execute(
                f"SELECT column_name, data_type "
                f"FROM information_schema.columns "
                f"WHERE table_name = '{tbl}' "
                f"ORDER BY ordinal_position"
            ).fetchall()
            schema[tbl] = [
                {"column": col, "type": dtype}
                for col, dtype in cols
            ]

        conn.close()
        return {
            "tool_name": tool_name,
            "db_type":   "duckdb",
            "db_path":   str(db_path),
            "schema":    schema,
            "error":     None,
        }

    except duckdb.Error as e:
        return _error_response(tool_name, "", str(e))


def list_tools() -> list[dict[str, Any]]:
    """
    Return all DuckDB tools with their descriptions.
    Called by mcp_server.py to build the combined tool list.
    """
    return [
        {
            "name":        name,
            "description": meta["description"],
            "db_type":     "duckdb",
            "db_path":     str(meta["path"]),
            "parameters":  [
                {
                    "name":        "sql",
                    "type":        "string",
                    "description": "SQL SELECT query to execute",
                    "required":    True,
                }
            ],
        }
        for name, meta in DUCKDB_TOOLS.items()
    ]


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_read_only(sql: str) -> bool:
    """Block any non-SELECT statement."""
    s = sql.strip().upper()
    blocked = ("INSERT", "UPDATE", "DELETE", "DROP",
               "CREATE", "ALTER", "TRUNCATE", "REPLACE", "MERGE")
    return s.startswith("SELECT") and not any(kw in s for kw in blocked)


def _error_response(tool_name: str, sql: str, msg: str) -> dict[str, Any]:
    return {
        "result":         [],
        "query_used":     sql,
        "db_type":        "duckdb",
        "tool_name":      tool_name,
        "db_path":        "",
        "row_count":      0,
        "execution_time": 0,
        "error":          None,
    }