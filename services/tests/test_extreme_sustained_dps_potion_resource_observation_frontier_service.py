from __future__ import annotations

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.extreme_sustained_dps_potion_resource_observation_frontier_service import (
    ExtremeSustainedDPSPotionResourceObservationFrontierService,
)
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=7.0,
        actions=(
            RotationAction(0.5, 0, RotationActionKind.SKILL, "A", "front"),
            RotationAction(1.0, 0, RotationActionKind.HEAVY_ATTACK, "HA", "front"),
            RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        ),
    )


def _heavy() -> RotationHeavyAttackCompletionEvidence:
    return RotationHeavyAttackCompletionEvidence(
        action_time_seconds=1.0,
        action_sequence=0,
        completion_time_seconds=2.8,
        fully_charged=True,
        verified_base_restore=None,
    )


def test_collects_actions_recovery_ticks_heavy_completion_and_additional_events() -> None:
    result = ExtremeSustainedDPSPotionResourceObservationFrontierService.collect(
        plan=_plan(),
        heavy_attack_completion_evidence=(_heavy(),),
        additional_resource_event_times=(3.5,),
        additional_resource_event_denominator_proven=True,
    )

    assert result.denominator_proven is True
    assert result.observation_times == (
        0.5,
        1.0,
        2.0,
        2.8,
        3.5,
        4.0,
        5.0,
        6.0,
    )


def test_missing_additional_resource_event_denominator_proof_fails_closed() -> None:
    result = ExtremeSustainedDPSPotionResourceObservationFrontierService.collect(
        plan=_plan(),
        heavy_attack_completion_evidence=(_heavy(),),
    )

    assert result.denominator_proven is False
    assert any(
        "denominator is not proven complete" in row
        for row in result.unresolved
    )


def test_extra_heavy_completion_evidence_fails_closed() -> None:
    extra = RotationHeavyAttackCompletionEvidence(
        action_time_seconds=6.0,
        action_sequence=0,
        completion_time_seconds=6.5,
        fully_charged=True,
        verified_base_restore=None,
    )
    result = ExtremeSustainedDPSPotionResourceObservationFrontierService.collect(
        plan=_plan(),
        heavy_attack_completion_evidence=(_heavy(), extra),
        additional_resource_event_denominator_proven=True,
    )

    assert result.denominator_proven is False
    assert any("no matching scheduled heavy" in row for row in result.unresolved)


def test_resource_observation_requires_strict_boolean_denominator_proof() -> None:
    with pytest.raises(
        TypeError,
        match="additional_resource_event_denominator_proven must be boolean",
    ):
        ExtremeSustainedDPSPotionResourceObservationFrontierService.collect(
            plan=_plan(),
            additional_resource_event_denominator_proven="false",  # type: ignore[arg-type]
        )


def test_resource_observation_requires_tuple_collections() -> None:
    with pytest.raises(TypeError, match="heavy_attack_completion_evidence must be a tuple"):
        ExtremeSustainedDPSPotionResourceObservationFrontierService.collect(
            plan=_plan(),
            heavy_attack_completion_evidence=[_heavy()],  # type: ignore[arg-type]
            additional_resource_event_denominator_proven=True,
        )

    with pytest.raises(TypeError, match="additional_resource_event_times must be a tuple"):
        ExtremeSustainedDPSPotionResourceObservationFrontierService.collect(
            plan=_plan(),
            additional_resource_event_times=[3.5],  # type: ignore[arg-type]
            additional_resource_event_denominator_proven=True,
        )


@pytest.mark.parametrize("value", (True, "3.5", None))
def test_resource_observation_rejects_coerced_additional_times(value) -> None:
    with pytest.raises(TypeError, match="observation times must be numeric"):
        ExtremeSustainedDPSPotionResourceObservationFrontierService.collect(
            plan=_plan(),
            additional_resource_event_times=(value,),  # type: ignore[arg-type]
            additional_resource_event_denominator_proven=True,
        )
