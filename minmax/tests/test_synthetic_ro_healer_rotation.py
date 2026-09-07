from minmax.duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from minmax.runtime_healer_wait_decision_provider import RuntimeHealerWaitDecisionProvider


def _skill(time_seconds: float, name: str) -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name=name,
        bar="front",
    )


def _ro_incentive() -> HealerHeavyAttackBuildIncentive:
    return HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Roaring Opportunist",
        source="verified synthetic RO evidence",
        recurrence_seconds=22.0,
        maximum_effect_duration_seconds=12.0,
    )


def _synthetic_plan() -> RotationPlan:
    return RotationPlan(
        character_name="Synthetic Warden",
        build_name="RO Healer",
        duration_seconds=31.0,
        actions=(
            _skill(0.0, "Long Buff"),
            _skill(2.0, "Long Buff"),
            _skill(3.0, "Action A"),
            _skill(24.0, "Long Buff"),
            _skill(26.0, "Long Buff"),
            _skill(28.0, "Long Buff"),
            _skill(29.0, "Action B"),
            _skill(30.0, "Action C"),
            _skill(31.0, "Action D"),
        ),
    )


def _rules() -> tuple[RotationRecastRule, ...]:
    return (
        RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front"),
        RotationRecastRule("Action A", duration_seconds=60.0, bar="front"),
        RotationRecastRule("Action B", duration_seconds=60.0, bar="front"),
        RotationRecastRule("Action C", duration_seconds=60.0, bar="front"),
        RotationRecastRule("Action D", duration_seconds=60.0, bar="front"),
    )


def test_synthetic_ro_healer_places_required_heavies_around_due_refresh() -> None:
    provider = RuntimeHealerWaitDecisionProvider(
        incentives=(_ro_incentive(),),
        required_window_seconds=1.8,
    )

    refined = DurationAwareRotationScheduler().refine(
        _synthetic_plan(),
        _rules(),
        wait_decision=provider,
    )

    heavies = [
        action.time_seconds
        for action in refined.actions
        if action.kind is RotationActionKind.HEAVY_ATTACK
    ]
    assert heavies == [2.0, 28.0]

    at_twenty_four = next(
        action
        for action in refined.actions
        if action.time_seconds == 24.0
        and action.kind is RotationActionKind.SKILL
    )
    assert at_twenty_four.name == "Long Buff"

    at_twenty_six = next(
        action
        for action in refined.actions
        if action.time_seconds == 26.0
        and action.kind is RotationActionKind.SKILL
    )
    assert at_twenty_six.name == "Action A"

    assert not any(action.time_seconds == 3.0 for action in refined.actions)
    assert not any(action.time_seconds == 29.0 for action in refined.actions)

    assert provider.runtime_states
    assert provider.runtime_states[0].incentive_name == "Roaring Opportunist"
    assert provider.runtime_states[0].last_trigger_seconds == 29.8

    assert any(
        "refresh obligation for 'Long Buff' claimed the 24s front-bar slot from 'Action A'"
        in item
        for item in refined.unresolved
    )
    assert any("reserved the front-bar timeline through 3.8s" in item for item in refined.unresolved)
    assert any("reserved the front-bar timeline through 29.8s" in item for item in refined.unresolved)
