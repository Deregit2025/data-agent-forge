"""Shared contracts and helpers for DB-specific sub-agents."""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from agent.self_correction import FailureContext, FailureType, RecoveryRouter, classify_exception

ToolExecutor = Callable[[str, dict[str, Any]], Any | Awaitable[Any]]


@dataclass(slots=True)
class SubQuery:
    id: str
    db_type: str
    task: str
    tool: str | None = None
    source_hint: str | None = None
    sql: str | None = None
    collection: str | None = None
    pipeline: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "db_type": self.db_type,
            "task": self.task,
            "tool": self.tool,
            "source_hint": self.source_hint,
            "sql": self.sql,
            "collection": self.collection,
            "pipeline": self.pipeline,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SubQuery":
        return cls(
            id=str(payload.get("id", "subquery")),
            db_type=str(payload["db_type"]),
            task=str(payload.get("task", "")),
            tool=payload.get("tool"),
            source_hint=payload.get("source_hint"),
            sql=payload.get("sql"),
            collection=payload.get("collection"),
            pipeline=payload.get("pipeline"),
            metadata=dict(payload.get("metadata", {})),
        )


def _maybe_await(value: Any | Awaitable[Any]) -> Awaitable[Any]:
    if inspect.isawaitable(value):
        return value  # type: ignore[return-value]

    async def _wrapped() -> Any:
        return value

    return _wrapped()


def _normalize_rows(raw_result: Any) -> list[Any]:
    if raw_result is None:
        return []
    if isinstance(raw_result, list):
        return raw_result
    if isinstance(raw_result, dict):
        for key in ("rows", "records", "result", "data"):
            rows = raw_result.get(key)
            if isinstance(rows, list):
                return rows
        return [raw_result]
    return [raw_result]


def discover_tools(db_type: str, tools_path: str | Path | None = None) -> list[str]:
    path = Path(tools_path) if tools_path else Path(__file__).resolve().parents[2] / "mcp" / "tools.yaml"
    if not path.exists():
        return []

    pattern = re.compile(rf"^\s{{2}}(query_{re.escape(db_type)}_[a-zA-Z0-9_]+):\s*$")
    discovered: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.match(line)
            if match:
                discovered.append(match.group(1))
    return discovered


class BaseSubAgent:
    db_type: str = ""

    def __init__(self, *, available_tools: list[str] | None = None, tools_path: str | Path | None = None) -> None:
        if available_tools is not None:
            self.available_tools = available_tools
        else:
            self.available_tools = discover_tools(self.db_type, tools_path=tools_path)

    def select_tool(self, sub_query: SubQuery) -> str:
        if sub_query.tool:
            return sub_query.tool

        if sub_query.source_hint:
            hint = sub_query.source_hint.lower()
            for tool in self.available_tools:
                if hint in tool.lower():
                    return tool

        if self.available_tools:
            return self.available_tools[0]

        raise ValueError(f"No configured tools found for db_type={self.db_type}")

    def build_payload(self, sub_query: SubQuery) -> dict[str, Any]:
        raise NotImplementedError

    async def execute(
        self,
        sub_query: SubQuery | dict[str, Any],
        *,
        tool_executor: ToolExecutor,
        recovery_router: RecoveryRouter | None = None,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        query = sub_query if isinstance(sub_query, SubQuery) else SubQuery.from_dict(sub_query)
        router = recovery_router or RecoveryRouter()
        current_task = query.as_dict()
        attempts = 0
        last_error = ""

        while attempts <= max_retries:
            attempts += 1
            working_query = SubQuery.from_dict(current_task)

            try:
                tool_name = self.select_tool(working_query)
                payload = self.build_payload(working_query)
                raw_result = await _maybe_await(tool_executor(tool_name, payload))
                return {
                    "id": working_query.id,
                    "db_type": self.db_type,
                    "tool": tool_name,
                    "status": "ok",
                    "attempts": attempts,
                    "rows": _normalize_rows(raw_result),
                    "raw_result": raw_result,
                    "metadata": working_query.metadata,
                }
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                failure_type = classify_exception(exc)
                context = FailureContext(
                    failure_type=failure_type,
                    error_message=last_error,
                    db_type=self.db_type,
                    attempt=attempts,
                    max_attempts=max_retries + 1,
                )
                action = router.route(context)
                if not action.retryable or attempts > max_retries:
                    return {
                        "id": working_query.id,
                        "db_type": self.db_type,
                        "status": "error",
                        "failure_type": failure_type.value,
                        "attempts": attempts,
                        "error": last_error,
                        "metadata": {
                            **working_query.metadata,
                            "recovery_strategy": action.strategy.value,
                        },
                    }
                current_task = router.apply_patch(current_task, action)

        return {
            "id": query.id,
            "db_type": self.db_type,
            "status": "error",
            "failure_type": FailureType.CONTRACT_VIOLATION.value,
            "attempts": attempts,
            "error": last_error or "Unknown sub-agent execution error",
            "metadata": query.metadata,
        }
