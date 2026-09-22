from __future__ import annotations

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from services.extreme_sustained_dps_heavy_attack_window_discovery_service import (
    ExtremeSustainedDPSHeavyAttackChannelBlock,
    ExtremeSustainedDPSHeavyAttackWindowDiscoveryService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


def _skill(time_seconds, name, *, bar="front", sequence=0):
    return RotationAction(
        time_seconds,
        sequence,
        RotationActionKind.SKILL,
        name,
        bar,
    )


def _seed(actions, *, duration=8.0):
    return GeneratedRotationCandidate(
        candidate_id="seed",
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=duration,
            actions=tuple(actions),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _rules():
    return (
        RotationRecastRule("Long Buff", 10.0, bar="front"),
        RotationRecastRule("A", 20.0, bar="front"),
        RotationRecastRule("B", 20.0, bar="front"),
        RotationRecastRule("C", 20.0, bar="front"),
        RotationRecastRule("Back", 20.0, bar="back"),
    )


def test_discovers_soft_slot_that_can_displace_same_bar_skill() -> None:
    seed = _seed(
        (
            _skill(0.0, "Long Buff"),
            _skill(2.0, "Long Buff"),
            _skill(3.0, "A"),
            _skill(4.0, "B"),
            _skill(5.0, "C"),
        ),
        duration=5.0,
    )

    result = ExtremeSustainedDPSHeavyAttackWindowDiscoveryService.discover(
        seed=seed,
        duration_rules=_rules(),
        channel_block_denominator_proven=True,
    )

    keys = tuple((row.time_seconds, row.sequence) for row in result.windows)
    assert (2.0, 0) in keys
    candidate = ExtremeSustainedDPSHeavyAttackWindowDiscoveryService.materialize(
        seed=seed,
        windows=tuple(row for row in result.windows if row.time_seconds == 2.0),
        duration_rules=_rules(),
    )
    assert any(
        action.kind is RotationActionKind.HEAVY_ATTACK
        and action.time_seconds == 2.0
        for action in candidate.plan.actions
    )
    assert not any(action.time_seconds == 3.0 for action in candidate.plan.actions)
    assert any(
        action.kind is RotationActionKind.SKILL
        and action.time_seconds == 4.0
        and action.name == "A"
        for action in candidate.plan.actions
    )


def test_first_cast_and_due_refresh_slots_are_not_discovered() -> None:
    seed = _seed(
        (
            _skill(0.0, "Long Buff"),
            _skill(5.0, "A"),
        ),
        duration=8.0,
    )

    result = ExtremeSustainedDPSHeavyAttackWindowDiscoveryService.discover(
        seed=seed,
        duration_rules=_rules(),
        channel_block_denominator_proven=True,
    )

    assert result.windows == ()


def test_hard_bar_swap_boundary_blocks_channel() -> None:
    seed = _seed(
        (
            _skill(0.0, "Long Buff"),
            _skill(2.0, "Long Buff"),
            RotationAction(3.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _skill(4.0, "Back", bar="back"),
        ),
        duration=6.0,
    )

    result = ExtremeSustainedDPSHeavyAttackWindowDiscoveryService.discover(
        seed=seed,
        duration_rules=_rules(),
        channel_block_denominator_proven=True,
    )

    assert all(row.time_seconds != 2.0 for row in result.windows)


def test_explicit_encounter_channel_block_removes_overlapping_slot() -> None:
    seed = _seed(
        (
            _skill(0.0, "Long Buff"),
            _skill(2.0, "Long Buff"),
            _skill(4.0, "A"),
        ),
        duration=6.0,
    )

    result = ExtremeSustainedDPSHeavyAttackWindowDiscoveryService.discover(
        seed=seed,
        duration_rules=_rules(),
        channel_blocks=(
            ExtremeSustainedDPSHeavyAttackChannelBlock(
                2.5,
                3.0,
                "reviewed mechanic requires free movement",
            ),
        ),
        channel_block_denominator_proven=True,
    )

    assert all(row.time_seconds != 2.0 for row in result.windows)


def test_unproven_encounter_channel_block_family_keeps_discovery_open() -> None:
    seed = _seed(
        (
            _skill(0.0, "Long Buff"),
            _skill(2.0, "Long Buff"),
            _skill(4.0, "A"),
        ),
        duration=6.0,
    )

    result = ExtremeSustainedDPSHeavyAttackWindowDiscoveryService.discover(
        seed=seed,
        duration_rules=_rules(),
    )

    assert result.denominator_proven is False
    assert any(
        "channel-block denominator is not proven complete" in item
        for item in result.unresolved
    )
