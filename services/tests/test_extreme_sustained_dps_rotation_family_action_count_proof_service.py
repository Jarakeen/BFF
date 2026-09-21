from __future__ import annotations

from services.extreme_sustained_dps_rotation_family_action_count_proof_service import (
    ExtremeSustainedDPSAdditionalDamageActionCountProof,
    ExtremeSustainedDPSRotationFamilyActionCountProofService,
)
from services.extreme_sustained_dps_rotation_plan_frontier_service import (
    ExtremeSustainedDPSRotationFamilyFrontier,
)


def _frontier(front=2, back=2, *, proven=True):
    return ExtremeSustainedDPSRotationFamilyFrontier(
        front_skill_count=front,
        back_skill_count=back,
        front_order_count=2,
        back_order_count=2,
        starting_route_count=2 if front and back else 1,
        weave_state_count=2,
        candidate_count=16,
        denominator_proven=proven,
        evidence=(),
        unresolved=(),
    )


def test_two_bar_seed_count_is_proven_without_materializing_permutations() -> None:
    result = ExtremeSustainedDPSRotationFamilyActionCountProofService.prove(
        _frontier(),
        duration_seconds=5.0,
    )

    # Pattern for either route is skill, skill, swap, skill, skill, swap.
    # Inclusive 0..5 horizon schedules six ticks: four skill ticks.
    # Weave-on => 8 damage-bearing actions.
    assert result.seed_maximum_damage_action_count == 8
    assert result.maximum_damage_action_count == 8
    assert result.proof.complete is True


def test_one_bar_family_counts_every_inclusive_tick_as_skill() -> None:
    result = ExtremeSustainedDPSRotationFamilyActionCountProofService.prove(
        _frontier(front=2, back=0),
        duration_seconds=4.0,
    )

    # Five inclusive ticks, all skill steps, weave-on => 10 actions.
    assert result.seed_maximum_damage_action_count == 10
    assert result.proof.complete is True


def test_proven_additional_policy_damage_actions_extend_safe_ceiling() -> None:
    result = ExtremeSustainedDPSRotationFamilyActionCountProofService.prove(
        _frontier(),
        duration_seconds=5.0,
        additional_policy_damage_actions=ExtremeSustainedDPSAdditionalDamageActionCountProof(
            maximum_additional_damage_actions=3,
            proven_safe=True,
            source="Ultimate cadence proof",
        ),
    )

    assert result.seed_maximum_damage_action_count == 8
    assert result.maximum_damage_action_count == 11
    assert result.proof.complete is True


def test_unproven_additional_policy_count_forces_open() -> None:
    result = ExtremeSustainedDPSRotationFamilyActionCountProofService.prove(
        _frontier(),
        duration_seconds=5.0,
        additional_policy_damage_actions=ExtremeSustainedDPSAdditionalDamageActionCountProof(
            maximum_additional_damage_actions=3,
            proven_safe=False,
            source="heuristic",
        ),
    )

    assert result.proof.complete is False
    assert any("not proven safe" in row for row in result.unresolved)


def test_unproven_frontier_cannot_promote_action_count_proof() -> None:
    result = ExtremeSustainedDPSRotationFamilyActionCountProofService.prove(
        _frontier(proven=False),
        duration_seconds=5.0,
    )

    assert result.proof.complete is False
