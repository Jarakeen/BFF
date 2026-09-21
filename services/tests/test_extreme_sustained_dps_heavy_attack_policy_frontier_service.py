from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.extreme_sustained_dps_heavy_attack_policy_frontier_service import (
    ExtremeSustainedDPSHeavyAttackPolicyFrontierService,
    ExtremeSustainedDPSHeavyAttackWindow,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


def _seed():
    return GeneratedRotationCandidate(
        candidate_id="seed",
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=10.0,
            actions=(
                RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
                RotationAction(0.0, 1, RotationActionKind.SKILL, name="A", bar="front"),
                RotationAction(2.0, 0, RotationActionKind.SKILL, name="B", bar="front"),
                RotationAction(4.0, 0, RotationActionKind.SKILL, name="C", bar="front"),
            ),
        ),
        refresh_leads=(),
    )


def test_heavy_policy_replaces_skill_removes_same_timestamp_la_and_proves_completion() -> None:
    result = ExtremeSustainedDPSHeavyAttackPolicyFrontierService().expand(
        seed=_seed(),
        windows=(ExtremeSustainedDPSHeavyAttackWindow(0.0, 1, "front"),),
    )

    assert result.denominator_proven is True
    assert tuple(row.policy_id for row in result.candidates) == (
        "heavy:none",
        "heavy:0/1",
    )
    heavy = result.candidates[1]
    assert heavy.completion_evidence_count == 1
    zero_actions = tuple(
        action
        for action in heavy.candidate.plan.actions
        if abs(action.time_seconds) <= 1e-9
    )
    assert len(zero_actions) == 1
    assert zero_actions[0].kind is RotationActionKind.HEAVY_ATTACK


def test_colliding_window_is_not_retained() -> None:
    seed = GeneratedRotationCandidate(
        candidate_id="seed",
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=5.0,
            actions=(
                RotationAction(0.0, 0, RotationActionKind.SKILL, name="A", bar="front"),
                RotationAction(1.0, 0, RotationActionKind.SKILL, name="B", bar="front"),
            ),
        ),
        refresh_leads=(),
    )
    result = ExtremeSustainedDPSHeavyAttackPolicyFrontierService().expand(
        seed=seed,
        windows=(ExtremeSustainedDPSHeavyAttackWindow(0.0, 0, "front"),),
    )

    assert tuple(row.policy_id for row in result.candidates) == ("heavy:none",)


def test_non_overlapping_heavy_windows_expand_to_combination_family() -> None:
    result = ExtremeSustainedDPSHeavyAttackPolicyFrontierService().expand(
        seed=_seed(),
        windows=(
            ExtremeSustainedDPSHeavyAttackWindow(0.0, 1, "front"),
            ExtremeSustainedDPSHeavyAttackWindow(2.0, 0, "front"),
            ExtremeSustainedDPSHeavyAttackWindow(4.0, 0, "front"),
        ),
    )

    # Every start is 2s apart, so all 2^3 subsets are compatible.
    assert len(result.candidates) == 8
    assert result.denominator_proven is True


def test_unsafe_encounter_window_is_not_retained() -> None:
    result = ExtremeSustainedDPSHeavyAttackPolicyFrontierService().expand(
        seed=_seed(),
        windows=(
            ExtremeSustainedDPSHeavyAttackWindow(
                0.0,
                1,
                "front",
                encounter_allows_channel=False,
            ),
        ),
    )

    assert tuple(row.policy_id for row in result.candidates) == ("heavy:none",)
