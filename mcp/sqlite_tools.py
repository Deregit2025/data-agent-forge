import time
import sqlite3
from typing import Any
from pathlib import Path
from mcp.db_config import SQLITE_TOOLS


def execute_query(tool_name: str, sql: str) -> dict[str, Any]:
    """
    Execute a read-only SQL query against the SQLite file
    mapped to tool_name.

    Returns the same structured response as all other tool files.
    """
    tool = SQLITE_TOOLS.get(tool_name)
    if tool is None:
        return _error_response(tool_name, sql, f"Unknown tool: '{tool_name}'")

    if not _is_read_only(sql):
        return _error_response(
            tool_name, sql,
            "Write operations are not permitted. Only SELECT queries are allowed."
        )

    db_path = tool["path"]
    if not Path(db_path).exists():
        return _error_response(
            tool_name, sql,
            f"SQLite file not found at {db_path}. "
            "Check DAB_PATH is set correctly."
        )

    start = time.perf_counter()
    conn  = None
    try:
        # uri=True + mode=ro enforces read-only at the SQLite driver level
        conn = sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row

        cur  = conn.execute(sql)
        rows = cur.fetchall()

        elapsed = round(time.perf_counter() - start, 4)
        result  = [dict(row) for row in rows]

        return {
            "result":         result,
            "query_used":     sql,
            "db_type":        "sqlite",
            "tool_name":      tool_name,
            "db_path":        str(db_path),
            "row_count":      len(result),
            "execution_time": elapsed,
            "error":          None,
        }

    except sqlite3.Error as e:
        elapsed = round(time.perf_counter() - start, 4)
        return {
            "result":         [],
            "query_used":     sql,
            "db_type":        "sqlite",
            "tool_name":      tool_name,
            "db_path":        str(db_path),
            "row_count":      0,
            "execution_time": elapsed,
            "error":          str(e),
        }
    finally:
        if conn:
            conn.close()


def get_schema(tool_name: str) -> dict[str, Any]:
    """
    Return the full schema of the SQLite database mapped to tool_name.
    Uses sqlite_master to discover all tables and their columns.
    Used by utils/schema_introspector.py to populate AGENT.md and KB files.
    """
    tool = SQLITE_TOOLS.get(tool_name)
    if tool is None:
        return _error_response(tool_name, "", f"Unknown tool: '{tool_name}'")

    db_path = tool["path"]
    if not Path(db_path).exists():
        return _error_response(
            tool_name, "",
            f"SQLite file not found at {db_path}."
        )

    conn = None
    try:
        conn = sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
            check_same_thread=False,
        )

        cur    = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cur.fetchall()]

        schema = {}
        for tbl in tables:
            cur = conn.execute(f"PRAGMA table_info('{tbl}')")
            schema[tbl] = [
                {
                    "column":   row[1],
                    "type":     row[2],
                    "nullable": row[3] == 0,
                    "pk":       row[5] == 1,
                }
                for row in cur.fetchall()
            ]

        return {
            "tool_name": tool_name,
            "db_type":   "sqlite",
            "db_path":   str(db_path),
            "schema":    schema,
            "error":     None,
        }

    except sqlite3.Error as e:
        return _error_response(tool_name, "", str(e))
    finally:
        if conn:
            conn.close()


def list_tools() -> list[dict[str, Any]]:
    """
    Return all SQLite tools with their descriptions.
    Called by mcp_server.py to build the combined tool list.
    """
    return [
        {
            "name":        name,
            "description": meta["description"],
            "db_type":     "sqlite",
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
        for name, meta in SQLITE_TOOLS.items()
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
        "db_type":        "sqlite",
        "tool_name":      tool_name,
        "db_path":        "",
        "row_count":      0,
        "execution_time": 0,
        "error":          msg,
    }