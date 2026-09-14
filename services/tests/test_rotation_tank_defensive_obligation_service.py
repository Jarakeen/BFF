from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
    RotationTankDefensiveObligationService,
)


def _candidate(*actions: RotationAction) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="tank-plan",
        plan=RotationPlan(
            character_name="Tank",
            build_name="Main Tank",
            duration_seconds=30.0,
            actions=tuple(actions),
        ),
        refresh_leads=(),
    )


def test_block_satisfies_block_only_window() -> None:
    candidate = _candidate(
        RotationAction(10.0, 0, RotationActionKind.BLOCK, bar="front"),
    )
    obligation = RotationTankDefensiveObligation(
        obligation_id="crashing-wave",
        window_start_seconds=9.5,
        window_end_seconds=10.5,
        allowed_actions=(RotationActionKind.BLOCK,),
        provenance=("reviewed encounter fact",),
    )

    result = RotationTankDefensiveObligationService().evaluate_candidate(
        candidate=candidate,
        obligations=(obligation,),
    )

    assert result.satisfied is True
    assert result.candidate_id == "tank-plan"
    assert "crashing-wave" in result.reasons[0]


def test_dodge_does_not_satisfy_block_only_window() -> None:
    candidate = _candidate(
        RotationAction(10.0, 0, RotationActionKind.DODGE, bar="front"),
    )
    obligation = RotationTankDefensiveObligation(
        obligation_id="must-block",
        window_start_seconds=9.0,
        window_end_seconds=11.0,
        allowed_actions=(RotationActionKind.BLOCK,),
    )

    result = RotationTankDefensiveObligationService().evaluate_candidate(
        candidate=candidate,
        obligations=(obligation,),
    )

    assert result.satisfied is False
    assert "0 of 1 required defensive responses" in result.reasons[0]


def test_either_response_can_satisfy_either_policy() -> None:
    candidate = _candidate(
        RotationAction(7.0, 0, RotationActionKind.DODGE, bar="back"),
    )
    obligation = RotationTankDefensiveObligation(
        obligation_id="block-or-dodge",
        window_start_seconds=6.5,
        window_end_seconds=7.5,
        allowed_actions=(RotationActionKind.BLOCK, RotationActionKind.DODGE),
    )

    result = RotationTankDefensiveObligationService().evaluate_candidate(
        candidate=candidate,
        obligations=(obligation,),
    )

    assert result.satisfied is True


def test_bar_specific_obligation_does_not_count_other_bar() -> None:
    candidate = _candidate(
        RotationAction(12.0, 0, RotationActionKind.BLOCK, bar="back"),
    )
    obligation = RotationTankDefensiveObligation(
        obligation_id="front-block",
        window_start_seconds=11.0,
        window_end_seconds=13.0,
        allowed_actions=(RotationActionKind.BLOCK,),
        bar="front",
    )

    result = RotationTankDefensiveObligationService().evaluate_candidate(
        candidate=candidate,
        obligations=(obligation,),
    )

    assert result.satisfied is False


def test_minimum_response_count_is_explicit_policy() -> None:
    candidate = _candidate(
        RotationAction(4.0, 0, RotationActionKind.BLOCK),
        RotationAction(5.0, 0, RotationActionKind.DODGE),
    )
    obligation = RotationTankDefensiveObligation(
        obligation_id="double-response",
        window_start_seconds=3.0,
        window_end_seconds=6.0,
        allowed_actions=(RotationActionKind.BLOCK, RotationActionKind.DODGE),
        minimum_responses=2,
    )

    result = RotationTankDefensiveObligationService().evaluate_candidate(
        candidate=candidate,
        obligations=(obligation,),
    )

    assert result.satisfied is True


def test_missing_obligation_is_unresolved_not_pass() -> None:
    result = RotationTankDefensiveObligationService().evaluate_candidate(
        candidate=_candidate(),
        obligations=(),
    )

    assert result.satisfied is None
    assert "no explicit source-backed obligation supplied" in result.reasons[0]


def test_duplicate_obligation_ids_fail_closed() -> None:
    candidate = _candidate()
    first = RotationTankDefensiveObligation(
        obligation_id="duplicate",
        window_start_seconds=1.0,
        window_end_seconds=2.0,
        allowed_actions=(RotationActionKind.BLOCK,),
    )
    second = RotationTankDefensiveObligation(
        obligation_id="duplicate",
        window_start_seconds=3.0,
        window_end_seconds=4.0,
        allowed_actions=(RotationActionKind.DODGE,),
    )

    try:
        RotationTankDefensiveObligationService().evaluate_candidate(
            candidate=candidate,
            obligations=(first, second),
        )
    except ValueError as exc:
        assert "duplicate tank defensive obligation id" in str(exc)
    else:
        raise AssertionError("expected duplicate obligation ids to fail closed")


def test_invalid_response_kind_is_rejected() -> None:
    try:
        RotationTankDefensiveObligation(
            obligation_id="invalid",
            window_start_seconds=1.0,
            window_end_seconds=2.0,
            allowed_actions=(RotationActionKind.SKILL,),
        )
    except ValueError as exc:
        assert "block and/or dodge" in str(exc)
    else:
        raise AssertionError("expected non-defensive action kind to be rejected")
