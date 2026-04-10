"""Recovery router that maps typed failures to retry strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent.self_correction.failure_types import FailureContext, FailureType


class RecoveryStrategy(str, Enum):
    REWRITE_QUERY = "rewrite_query"
    ALIGN_JOIN_KEYS = "align_join_keys"
    SWITCH_DB_ADAPTER = "switch_db_adapter"
    ELEVATE_PERMISSIONS = "elevate_permissions"
    COMPACT_CONTEXT = "compact_context"
    APPLY_DATA_QUALITY_GUARDS = "apply_data_quality_guards"
    REPAIR_CONTRACT = "repair_contract"


@dataclass(slots=True)
class RecoveryAction:
    strategy: RecoveryStrategy
    retryable: bool = True
    suppress_error: bool = True
    note: str = ""
    task_patch: dict[str, Any] = field(default_factory=dict)


class RecoveryRouter:
    """Routes failures to retry actions without surfacing raw errors to users."""

    def route(self, context: FailureContext) -> RecoveryAction:
        if context.failure_type == FailureType.QUERY_SYNTAX_ERROR:
            return RecoveryAction(
                strategy=RecoveryStrategy.REWRITE_QUERY,
                note="Rewrite query using stricter syntax guidance.",
                task_patch={"retry_hint": "rewrite_with_valid_syntax", "strict_syntax": True},
            )

        if context.failure_type == FailureType.JOIN_KEY_MISMATCH:
            return RecoveryAction(
                strategy=RecoveryStrategy.ALIGN_JOIN_KEYS,
                note="Normalize join keys and enforce key compatibility before join.",
                task_patch={"retry_hint": "normalize_join_keys", "join_validation": True},
            )

        if context.failure_type == FailureType.DATABASE_TYPE_ERROR:
            return RecoveryAction(
                strategy=RecoveryStrategy.SWITCH_DB_ADAPTER,
                note="Re-route query through DB-compatible adapter.",
                task_patch={"retry_hint": "switch_db_adapter", "force_db_type": context.db_type},
            )

        if context.failure_type == FailureType.PERMISSION_DENIED:
            return RecoveryAction(
                strategy=RecoveryStrategy.ELEVATE_PERMISSIONS,
                retryable=False,
                note="Permission issue should be escalated to runtime policy.",
                task_patch={"retry_hint": "permission_escalation_required"},
            )

        if context.failure_type == FailureType.CONTEXT_OVERFLOW:
            return RecoveryAction(
                strategy=RecoveryStrategy.COMPACT_CONTEXT,
                note="Shrink payload and request smaller result set.",
                task_patch={"retry_hint": "compact_context", "limit_rows": 100},
            )

        if context.failure_type == FailureType.DATA_QUALITY_ERROR:
            return RecoveryAction(
                strategy=RecoveryStrategy.APPLY_DATA_QUALITY_GUARDS,
                note="Add null handling and data quality filters.",
                task_patch={"retry_hint": "quality_filters", "drop_nulls": True},
            )

        return RecoveryAction(
            strategy=RecoveryStrategy.REPAIR_CONTRACT,
            note="Repair output schema to match contract validator requirements.",
            task_patch={"retry_hint": "repair_contract", "strict_output_contract": True},
        )

    @staticmethod
    def apply_patch(task: dict[str, Any], action: RecoveryAction) -> dict[str, Any]:
        updated = dict(task)
        metadata = dict(updated.get("metadata", {}))
        metadata["recovery_strategy"] = action.strategy.value
        metadata["recovery_note"] = action.note
        updated["metadata"] = metadata
        updated.update(action.task_patch)
        return updated
