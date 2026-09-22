from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.ultimate_resource_timeline import UltimateGenerationEvent, UltimateSpendRule
from services.extreme_sustained_dps_delayed_ultimate_policy_frontier_service import (
    ExtremeSustainedDPSDelayedUltimatePolicyFrontierService,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=4.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "A", "front"),
            RotationAction(1.0, 0, RotationActionKind.SKILL, "B", "front"),
            RotationAction(2.0, 0, RotationActionKind.SKILL, "C", "front"),
            RotationAction(3.0, 0, RotationActionKind.SKILL, "D", "back"),
            RotationAction(4.0, 0, RotationActionKind.SKILL, "E", "front"),
        ),
    )


def test_frontier_enumerates_every_legal_delayed_cast_sequence() -> None:
    result = ExtremeSustainedDPSDelayedUltimatePolicyFrontierService().build(
        plan=_plan(),
        bar="front",
        spend_rule=UltimateSpendRule("Ultimate X", 100.0),
        starting_ultimate=100.0,
        generation_events=(
            UltimateGenerationEvent(1.5, 100.0, "gain"),
        ),
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 10
    assert result.policies[0].cast_slots == ()
    assert any(
        row.cast_slots == ((0.0, 0), (2.0, 0))
        for row in result.policies
    )
    assert any(
        row.cast_slots == ((1.0, 0), (4.0, 0))
        for row in result.policies
    )


def test_same_timestamp_generation_cannot_fund_same_timestamp_cast() -> None:
    result = ExtremeSustainedDPSDelayedUltimatePolicyFrontierService().build(
        plan=_plan(),
        bar="front",
        spend_rule=UltimateSpendRule("Ultimate X", 100.0),
        starting_ultimate=0.0,
        generation_events=(
            UltimateGenerationEvent(1.0, 100.0, "same-time gain"),
        ),
    )

    assert all(
        (1.0, 0) not in row.cast_slots
        for row in result.policies
    )
    assert any(
        row.cast_slots == ((2.0, 0),)
        for row in result.policies
    )


def test_frontier_only_uses_selected_bar_skill_slots() -> None:
    result = ExtremeSustainedDPSDelayedUltimatePolicyFrontierService().build(
        plan=_plan(),
        bar="back",
        spend_rule=UltimateSpendRule("Ultimate X", 100.0),
        starting_ultimate=100.0,
    )

    assert tuple(row.cast_slots for row in result.policies) == (
        (),
        ((3.0, 0),),
    )


def test_repeated_casts_consume_shared_ultimate_balance() -> None:
    result = ExtremeSustainedDPSDelayedUltimatePolicyFrontierService().build(
        plan=_plan(),
        bar="front",
        spend_rule=UltimateSpendRule("Ultimate X", 100.0),
        starting_ultimate=199.0,
    )

    assert not any(
        len(row.cast_slots) > 1
        for row in result.policies
    )



def test_scheduler_slot_identity_mismatch_fails_closed() -> None:
    class _BrokenScheduler:
        @staticmethod
        def apply(plan, rules):
            return plan

    result = ExtremeSustainedDPSDelayedUltimatePolicyFrontierService(
        scheduler=_BrokenScheduler()
    ).build(
        plan=_plan(),
        bar="front",
        spend_rule=UltimateSpendRule("Ultimate X", 100.0),
        starting_ultimate=100.0,
    )

    assert result.denominator_proven is False
    assert any(
        "did not preserve selected cast-slot identity" in row
        for row in result.unresolved
    )
