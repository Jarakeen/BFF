from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.heavy_attack_runtime_state import HeavyAttackEffectRuntimeState
from minmax.rotation_plan import RotationAction, RotationActionKind
from minmax.rotation_recast import RotationRecastRule
from minmax.rotation_wait_decision import PrematureRecastDecisionContext
from minmax.runtime_healer_wait_decision_provider import RuntimeHealerWaitDecisionProvider


def _incentive() -> HealerHeavyAttackBuildIncentive:
    return HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Roaring Opportunist",
        source="verified test evidence",
        recurrence_seconds=22.0,
        maximum_effect_duration_seconds=12.0,
    )


def _context(*, next_decision=5.0, next_due=()) -> PrematureRecastDecisionContext:
    slot = RotationAction(2.0, 1, RotationActionKind.SKILL, "Long Buff", "front")
    return PrematureRecastDecisionContext(
        time_seconds=2.0,
        bar="front",
        candidate=slot,
        slot=slot,
        next_due=tuple(next_due),
        rules=(RotationRecastRule("Long Buff", 10.0, bar="front"),),
        next_decision_time_seconds=next_decision,
        plan_end_seconds=10.0,
    )


def test_due_required_heavy_is_scheduled_when_channel_fits() -> None:
    provider = RuntimeHealerWaitDecisionProvider(
        incentives=(_incentive(),),
        required_window_seconds=1.8,
    )

    action = provider(_context(next_decision=5.0))

    assert action is not None
    assert action.kind is RotationActionKind.HEAVY_ATTACK
    assert action.bar == "front"
    assert action.time_seconds == 2.0


def test_due_required_heavy_is_rejected_when_next_decision_cuts_channel_short() -> None:
    provider = RuntimeHealerWaitDecisionProvider(
        incentives=(_incentive(),),
        required_window_seconds=1.8,
    )

    action = provider(_context(next_decision=3.0))

    assert action is None


def test_locked_out_required_heavy_is_not_scheduled() -> None:
    provider = RuntimeHealerWaitDecisionProvider(
        incentives=(_incentive(),),
        required_window_seconds=1.8,
        runtime_states=(
            HeavyAttackEffectRuntimeState(
                incentive_name="Roaring Opportunist",
                bar="front",
                last_trigger_seconds=1.0,
            ),
        ),
    )

    action = provider(_context(next_decision=5.0))

    assert action is None


def test_due_required_heavy_is_rejected_when_refresh_lands_inside_channel() -> None:
    provider = RuntimeHealerWaitDecisionProvider(
        incentives=(_incentive(),),
        required_window_seconds=1.8,
    )

    action = provider(
        _context(
            next_decision=5.0,
            next_due=(("combat prayer", "front", 3.2),),
        )
    )

    assert action is None
