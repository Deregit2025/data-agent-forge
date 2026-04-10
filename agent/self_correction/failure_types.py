"""Failure taxonomy for the self-correction engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FailureType(str, Enum):
    """Typed failure categories used by the recovery router."""

    QUERY_SYNTAX_ERROR = "QuerySyntaxError"
    JOIN_KEY_MISMATCH = "JoinKeyMismatch"
    DATABASE_TYPE_ERROR = "DatabaseTypeError"
    PERMISSION_DENIED = "PermissionDenied"
    CONTEXT_OVERFLOW = "ContextOverflow"
    DATA_QUALITY_ERROR = "DataQualityError"
    CONTRACT_VIOLATION = "ContractViolation"


@dataclass(slots=True)
class FailureContext:
    """Structured context for routing recovery decisions."""

    failure_type: FailureType
    error_message: str
    db_type: str | None = None
    attempt: int = 1
    max_attempts: int = 3
    details: dict[str, Any] = field(default_factory=dict)


def classify_exception(exc: Exception) -> FailureType:
    """Classify a runtime exception into a typed failure."""
    message = str(exc).lower()

    if any(token in message for token in ("syntax", "parse", "unexpected token", "invalid sql")):
        return FailureType.QUERY_SYNTAX_ERROR

    if any(token in message for token in ("join key", "foreign key", "column mismatch", "key mismatch")):
        return FailureType.JOIN_KEY_MISMATCH

    if any(token in message for token in ("database type", "unsupported dialect", "wrong adapter")):
        return FailureType.DATABASE_TYPE_ERROR

    if any(token in message for token in ("permission denied", "forbidden", "not authorized", "access denied")):
        return FailureType.PERMISSION_DENIED

    if any(token in message for token in ("context length", "token limit", "prompt too long", "overflow")):
        return FailureType.CONTEXT_OVERFLOW

    if any(token in message for token in ("null rate", "missing values", "outlier", "data quality")):
        return FailureType.DATA_QUALITY_ERROR

    return FailureType.CONTRACT_VIOLATION
