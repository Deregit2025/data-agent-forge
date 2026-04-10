"""PostgreSQL sub-agent adapter."""

from __future__ import annotations

from typing import Any

from agent.sub_agents import BaseSubAgent, SubQuery


class PostgresSubAgent(BaseSubAgent):
    db_type = "postgres"

    def build_payload(self, sub_query: SubQuery) -> dict[str, Any]:
        statement = sub_query.sql or sub_query.task
        if not statement:
            raise ValueError("Postgres sub-query requires SQL text in `sql` or `task`.")
        return {"sql": statement, "statement": statement}
