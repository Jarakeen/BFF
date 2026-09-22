from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_potion_observation_frontier_service import (
    ExtremeSustainedDPSPotionObservationFrontierService,
)
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    RotationPeriodicDamageRuntimeProjection,
    RotationPeriodicDamageRuntimeProjectionEntry,
)
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=10.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Skill A", "front"),
            RotationAction(1.0, 1, RotationActionKind.LIGHT_ATTACK, "Light Attack", "front"),
            RotationAction(2.0, 0, RotationActionKind.HEAVY_ATTACK, "Heavy Attack", "front"),
            RotationAction(5.0, 0, RotationActionKind.ULTIMATE, "Ultimate X", "front"),
            RotationAction(6.0, 0, RotationActionKind.POTION, "Potion X"),
        ),
    )


def _periodic(*times: float, unresolved=()) -> RotationPeriodicDamageRuntimeProjection:
    parent = _plan().actions[0]
    entry = RotationPeriodicDamageRuntimeProjectionEntry(
        action=parent,
        coefficient_number=1,
        events=tuple(
            RuntimeEvent(
                time_seconds=float(time),
                sequence=index,
                trigger="damage_dealt",
                source="Skill A periodic",
            )
            for index, time in enumerate(times)
        ),
        active_end_time_seconds=max(times) if times else None,
        unresolved=tuple(unresolved),
    )
    return RotationPeriodicDamageRuntimeProjection(
        entries=(entry,),
        unresolved=(),
    )


def _heavy() -> RotationHeavyAttackCompletionEvidence:
    return RotationHeavyAttackCompletionEvidence(
        action_time_seconds=2.0,
        action_sequence=0,
        completion_time_seconds=3.8,
        fully_charged=True,
        verified_base_restore=None,
    )


def test_collects_direct_periodic_and_heavy_completion_observations() -> None:
    result = ExtremeSustainedDPSPotionObservationFrontierService.collect(
        plan=_plan(),
        periodic_projections=(_periodic(2.5, 4.5),),
        heavy_attack_completion_evidence=(_heavy(),),
    )

    assert result.denominator_proven is True
    assert result.observation_times == (0.0, 1.0, 2.5, 3.8, 4.5, 5.0)
    assert all(point.time_seconds != 2.0 for point in result.points)
    assert all(point.time_seconds != 6.0 for point in result.points)
    assert any(point.kind == "heavy_attack_completion" for point in result.points)
    assert sum(point.kind == "periodic_tick" for point in result.points) == 2


def test_scheduled_heavy_without_completion_evidence_fails_closed() -> None:
    result = ExtremeSustainedDPSPotionObservationFrontierService.collect(
        plan=_plan(),
    )

    assert result.denominator_proven is False
    assert any(
        "lacks verified completion evidence" in row
        for row in result.unresolved
    )


def test_unresolved_periodic_projection_fails_closed() -> None:
    result = ExtremeSustainedDPSPotionObservationFrontierService.collect(
        plan=_plan(),
        periodic_projections=(
            _periodic(2.5, unresolved=("periodic magnitude timing unresolved",)),
        ),
        heavy_attack_completion_evidence=(_heavy(),),
    )

    assert result.denominator_proven is False
    assert any(
        "periodic magnitude timing unresolved" in row
        for row in result.unresolved
    )


def test_extra_heavy_completion_evidence_fails_closed() -> None:
    extra = RotationHeavyAttackCompletionEvidence(
        action_time_seconds=9.0,
        action_sequence=0,
        completion_time_seconds=9.5,
        fully_charged=True,
        verified_base_restore=None,
    )
    result = ExtremeSustainedDPSPotionObservationFrontierService.collect(
        plan=_plan(),
        heavy_attack_completion_evidence=(_heavy(), extra),
    )

    assert result.denominator_proven is False
    assert any(
        "no scheduled Heavy Attack" in row
        for row in result.unresolved
    )
