from agent.self_correction.failure_types import FailureContext, FailureType
from agent.self_correction.recovery_router import RecoveryRouter


def test_recovery_router_maps_all_failure_types():
    router = RecoveryRouter()
    mapped = {}
    for failure_type in FailureType:
        action = router.route(
            FailureContext(
                failure_type=failure_type,
                error_message="synthetic test failure",
                db_type="sqlite",
            )
        )
        mapped[failure_type.value] = action.strategy.value

    assert mapped["QuerySyntaxError"] == "rewrite_query"
    assert mapped["JoinKeyMismatch"] == "align_join_keys"
    assert mapped["DatabaseTypeError"] == "switch_db_adapter"
    assert mapped["PermissionDenied"] == "elevate_permissions"
    assert mapped["ContextOverflow"] == "compact_context"
    assert mapped["DataQualityError"] == "apply_data_quality_guards"
    assert mapped["ContractViolation"] == "repair_contract"
