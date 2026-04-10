"""MongoDB sub-agent adapter."""

from __future__ import annotations

from typing import Any

from agent.sub_agents import BaseSubAgent, SubQuery


class MongoSubAgent(BaseSubAgent):
    db_type = "mongo"

    def build_payload(self, sub_query: SubQuery) -> dict[str, Any]:
        collection = sub_query.collection or "business"
        pipeline = sub_query.pipeline or []
        return {
            "collection": collection,
            "pipeline": pipeline,
            "task": sub_query.task,
        }
