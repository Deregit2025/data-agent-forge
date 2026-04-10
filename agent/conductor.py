"""Conductor agent with a LangGraph plan -> fan-out -> merge workflow."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, TypedDict

from agent.self_correction import RecoveryRouter
from agent.sub_agents import SubQuery, ToolExecutor
from agent.sub_agents.duckdb_agent import DuckDBSubAgent
from agent.sub_agents.mongo_agent import MongoSubAgent
from agent.sub_agents.postgres_agent import PostgresSubAgent
from agent.sub_agents.sqlite_agent import SQLiteSubAgent

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover
    END = "__end__"
    START = "__start__"
    StateGraph = None  # type: ignore[assignment]


class ConductorState(TypedDict, total=False):
    question: str
    sub_queries: list[dict[str, Any]]
    results: list[dict[str, Any]]
    final_answer: dict[str, Any]


@dataclass(slots=True)
class ConductorAgent:
    """ChiefJustice-style conductor that plans, delegates, and merges."""

    tool_executor: ToolExecutor
    recovery_router: RecoveryRouter = RecoveryRouter()

    def __post_init__(self) -> None:
        self.sub_agents = {
            "postgres": PostgresSubAgent(),
            "mongo": MongoSubAgent(),
            "sqlite": SQLiteSubAgent(),
            "duckdb": DuckDBSubAgent(),
        }
        self.graph = self._build_graph()

    async def run(self, question: str, sub_queries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        initial_state: ConductorState = {"question": question}
        if sub_queries:
            initial_state["sub_queries"] = sub_queries
        result = await self.graph.ainvoke(initial_state)
        return result["final_answer"]

    def _build_graph(self):
        if StateGraph is None:
            return _FallbackGraph(self._plan_node, self._fanout_node, self._merge_node)

        graph = StateGraph(ConductorState)
        graph.add_node("plan", self._plan_node)
        graph.add_node("fanout", self._fanout_node)
        graph.add_node("merge", self._merge_node)
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "fanout")
        graph.add_edge("fanout", "merge")
        graph.add_edge("merge", END)
        return graph.compile()

    async def _plan_node(self, state: ConductorState) -> ConductorState:
        if state.get("sub_queries"):
            return state

        question = state.get("question", "")
        state["sub_queries"] = self._decompose_question(question)
        return state

    async def _fanout_node(self, state: ConductorState) -> ConductorState:
        tasks = []
        for query in state.get("sub_queries", []):
            db_type = query.get("db_type")
            if db_type not in self.sub_agents:
                state.setdefault("results", []).append(
                    {
                        "id": query.get("id"),
                        "db_type": db_type,
                        "status": "error",
                        "error": f"Unsupported db_type={db_type}",
                    }
                )
                continue

            agent = self.sub_agents[db_type]
            tasks.append(
                agent.execute(
                    SubQuery.from_dict(query),
                    tool_executor=self.tool_executor,
                    recovery_router=self.recovery_router,
                )
            )

        if tasks:
            parallel_results = await asyncio.gather(*tasks)
            state["results"] = [*state.get("results", []), *parallel_results]
        else:
            state.setdefault("results", [])
        return state

    async def _merge_node(self, state: ConductorState) -> ConductorState:
        results = state.get("results", [])
        success = [result for result in results if result.get("status") == "ok"]
        failures = [result for result in results if result.get("status") != "ok"]
        state["final_answer"] = {
            "question": state.get("question", ""),
            "status": "partial_success" if failures and success else ("success" if success else "error"),
            "result_count": len(success),
            "error_count": len(failures),
            "results": success,
            "errors": failures,
        }
        return state

    def _decompose_question(self, question: str) -> list[dict[str, Any]]:
        normalized = question.lower()
        yelp_like = "yelp" in normalized or "review" in normalized or "business" in normalized

        # Default ChiefJustice decomposition fans out one task per DB adapter.
        return [
            {
                "id": "q-postgres-1",
                "db_type": "postgres",
                "task": "SELECT 1 AS healthcheck",
                "sql": "SELECT 1 AS healthcheck",
                "source_hint": "googlelocal" if not yelp_like else "bookreview",
            },
            {
                "id": "q-mongo-1",
                "db_type": "mongo",
                "task": "Aggregate Yelp-like business records",
                "collection": "business" if yelp_like else "articles",
                "pipeline": [{"$limit": 5}],
                "source_hint": "yelp" if yelp_like else "agnews",
            },
            {
                "id": "q-sqlite-1",
                "db_type": "sqlite",
                "task": "SELECT name FROM sqlite_master LIMIT 5",
                "sql": "SELECT name FROM sqlite_master LIMIT 5",
                "source_hint": "yelp" if yelp_like else "bookreview",
            },
            {
                "id": "q-duckdb-1",
                "db_type": "duckdb",
                "task": "SELECT 1 AS healthcheck",
                "sql": "SELECT 1 AS healthcheck",
                "source_hint": "music",
            },
        ]


class _FallbackGraph:
    """Small fallback runtime when LangGraph is unavailable."""

    def __init__(self, plan_node, fanout_node, merge_node) -> None:
        self._plan_node = plan_node
        self._fanout_node = fanout_node
        self._merge_node = merge_node

    async def ainvoke(self, state: ConductorState) -> ConductorState:
        state = await self._plan_node(state)
        state = await self._fanout_node(state)
        state = await self._merge_node(state)
        return state
