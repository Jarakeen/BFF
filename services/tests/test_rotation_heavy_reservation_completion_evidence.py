from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)


def _plan(*, reservation_line: str | None) -> RotationPlan:
    unresolved = () if reservation_line is None else (reservation_line,)
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(
            RotationAction(
                time_seconds=18.0,
                sequence=3,
                kind=RotationActionKind.HEAVY_ATTACK,
                bar="back",
            ),
        ),
        unresolved=unresolved,
    )


def test_reviewed_1_8_second_reserved_heavy_becomes_full_charge_evidence() -> None:
    plan = _plan(
        reservation_line=(
            "caller-proven heavy_attack at 18s reserved the back-bar timeline "
            "through 19.8s"
        )
    )

    evidence = (
        RotationHeavySustainProjectionService
        .completion_evidence_from_verified_reservations(plan)
    )

    assert len(evidence) == 1
    item = evidence[0]
    assert item.action_time_seconds == 18.0
    assert item.action_sequence == 3
    assert item.completion_time_seconds == 19.8
    assert item.fully_charged is True
    assert item.verified_base_restore is None
    assert "1.8s" in item.source


def test_old_2_2_second_reference_timing_is_not_promoted() -> None:
    plan = _plan(
        reservation_line=(
            "caller-proven heavy_attack at 18s reserved the back-bar timeline "
            "through 20.2s"
        )
    )

    assert (
        RotationHeavySustainProjectionService
        .completion_evidence_from_verified_reservations(plan)
        == ()
    )


def test_manual_heavy_without_verified_reservation_is_not_promoted() -> None:
    assert (
        RotationHeavySustainProjectionService
        .completion_evidence_from_verified_reservations(
            _plan(reservation_line=None)
        )
        == ()
    )


def test_reservation_must_match_the_heavy_bar() -> None:
    plan = _plan(
        reservation_line=(
            "caller-proven heavy_attack at 18s reserved the front-bar timeline "
            "through 19.8s"
        )
    )

    assert (
        RotationHeavySustainProjectionService
        .completion_evidence_from_verified_reservations(plan)
        == ()
    )


def test_non_heavy_reservation_provenance_is_not_promoted() -> None:
    plan = _plan(
        reservation_line=(
            "caller-proven skill at 18s reserved the back-bar timeline through 19.8s"
        )
    )

    assert (
        RotationHeavySustainProjectionService
        .completion_evidence_from_verified_reservations(plan)
        == ()
    )
