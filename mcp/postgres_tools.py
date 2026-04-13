import time
from typing import Any
import psycopg2
import psycopg2.extras

from mcp.db_config import PG_CONFIG, PG_TOOLS


def execute_query(tool_name: str, sql: str) -> dict[str, Any]:
    """
    Execute a read-only SQL query against the PostgreSQL database
    mapped to tool_name.

    Returns the same structured response as all other tool files
    so mcp_server.py can treat all four DB types identically.
    """
    tool = PG_TOOLS.get(tool_name)
    if tool is None:
        return _error_response(tool_name, sql, f"Unknown tool: '{tool_name}'")

    if not _is_read_only(sql):
        return _error_response(
            tool_name, sql,
            "Write operations are not permitted. Only SELECT queries are allowed."
        )

    start = time.perf_counter()
    conn  = None
    try:
        conn = psycopg2.connect(
            host=PG_CONFIG["host"],
            port=PG_CONFIG["port"],
            user=PG_CONFIG["user"],
            password=PG_CONFIG["password"],
            dbname=tool["db"],
        )
        # open a read-only transaction — belt and braces
        conn.set_session(readonly=True, autocommit=True)

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()

        elapsed = round(time.perf_counter() - start, 4)
        result  = [dict(row) for row in rows]

        return {
            "result":         result,
            "query_used":     sql,
            "db_type":        "postgres",
            "tool_name":      tool_name,
            "database":       tool["db"],
            "row_count":      len(result),
            "execution_time": elapsed,
            "error":          None,
        }

    except psycopg2.Error as e:
        elapsed = round(time.perf_counter() - start, 4)
        return {
            "result":         [],
            "query_used":     sql,
            "db_type":        "postgres",
            "tool_name":      tool_name,
            "database":       tool.get("db", ""),
            "row_count":      0,
            "execution_time": elapsed,
            "error":          str(e),
        }
    finally:
        if conn:
            conn.close()


def get_schema(tool_name: str) -> dict[str, Any]:
    """
    Return the full schema of the PostgreSQL database mapped to tool_name.
    Used by utils/schema_introspector.py to populate AGENT.md and KB files.
    """
    tool = PG_TOOLS.get(tool_name)
    if tool is None:
        return _error_response(tool_name, "", f"Unknown tool: '{tool_name}'")

    conn = None
    try:
        conn = psycopg2.connect(
            host=PG_CONFIG["host"],
            port=PG_CONFIG["port"],
            user=PG_CONFIG["user"],
            password=PG_CONFIG["password"],
            dbname=tool["db"],
        )
        conn.set_session(readonly=True, autocommit=True)

        with conn.cursor() as cur:
            # get all tables in public schema
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]

            schema = {}
            for tbl in tables:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name   = %s
                    ORDER BY ordinal_position
                """, (tbl,))
                schema[tbl] = [
                    {
                        "column":   col,
                        "type":     dtype,
                        "nullable": nullable == "YES",
                    }
                    for col, dtype, nullable in cur.fetchall()
                ]

        return {
            "tool_name": tool_name,
            "db_type":   "postgres",
            "database":  tool["db"],
            "schema":    schema,
            "error":     None,
        }

    except psycopg2.Error as e:
        return _error_response(tool_name, "", str(e))
    finally:
        if conn:
            conn.close()


def list_tools() -> list[dict[str, Any]]:
    """
    Return all PostgreSQL tools with their descriptions.
    Called by mcp_server.py to build the combined tool list.
    """
    return [
        {
            "name":        name,
            "description": meta["description"],
            "db_type":     "postgres",
            "database":    meta["db"],
            "parameters":  [
                {
                    "name":        "sql",
                    "type":        "string",
                    "description": "SQL SELECT query to execute",
                    "required":    True,
                }
            ],
        }
        for name, meta in PG_TOOLS.items()
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
        "db_type":        "postgres",
        "tool_name":      tool_name,
        "database":       "",
        "row_count":      0,
        "execution_time": 0,
        "error":          msg,
    }