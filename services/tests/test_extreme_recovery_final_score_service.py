from services.extreme_recovery_final_score_service import (
    ExtremeRecoveryFinalScoreService,
    ExtremeRecoveryProofGate,
    ExtremeRecoveryScoreComponent,
)


def test_composes_additive_then_percent_recovery_math():
    row = ExtremeRecoveryFinalScoreService.compose(
        objective_key="health_recovery",
        base_value=309.0,
        additive_components=(
            ExtremeRecoveryScoreComponent("race", 90.0),
            ExtremeRecoveryScoreComponent("class", 1950.0),
        ),
        percent_components=(
            ExtremeRecoveryScoreComponent("Constitution", 28.0),
            ExtremeRecoveryScoreComponent("Major Fortitude", 30.0),
        ),
        proof_gates=(ExtremeRecoveryProofGate("route", True),),
    )

    assert row.pre_percent_total == 2349.0
    assert row.total_percent == 58.0
    assert round(row.final_value, 3) == 3711.42
    assert row.proof_complete is True


def test_failed_proof_gate_keeps_numeric_score_but_not_record_closure():
    row = ExtremeRecoveryFinalScoreService.compose(
        objective_key="health_recovery",
        base_value=309.0,
        additive_components=(),
        percent_components=(),
        proof_gates=(ExtremeRecoveryProofGate("ultimate witness", False),),
    )

    assert row.final_value == 309.0
    assert row.proof_complete is False


def test_duplicate_component_fails_closed():
    row = ExtremeRecoveryFinalScoreService.compose(
        objective_key="health_recovery",
        base_value=309.0,
        additive_components=(
            ExtremeRecoveryScoreComponent("same", 1.0),
            ExtremeRecoveryScoreComponent("SAME", 2.0),
        ),
        percent_components=(),
    )

    assert row.unresolved == ("duplicate additive Recovery component: SAME",)
    assert row.proof_complete is False


def test_non_recovery_objective_fails_closed():
    row = ExtremeRecoveryFinalScoreService.compose(
        objective_key="max_health",
        base_value=1.0,
        additive_components=(),
        percent_components=(),
    )

    assert row.unresolved
    assert row.proof_complete is False
