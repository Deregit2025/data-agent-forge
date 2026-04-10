"""DuckDB sub-agent adapter."""

from __future__ import annotations

from agent.sub_agents import BaseSubAgent, SubQuery


class DuckDBSubAgent(BaseSubAgent):
    db_type = "duckdb"

    def build_payload(self, sub_query: SubQuery) -> dict[str, str]:
        statement = sub_query.sql or sub_query.task
        if not statement:
            raise ValueError("DuckDB sub-query requires SQL text in `sql` or `task`.")
        return {"sql": statement, "statement": statement}
