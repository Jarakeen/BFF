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


def _context(
    *,
    time_seconds=2.0,
    next_decision=3.0,
    hard_boundary=5.0,
    next_due=(),
    plan_end=40.0,
) -> PrematureRecastDecisionContext:
    slot = RotationAction(time_seconds, 1, RotationActionKind.SKILL, "Long Buff", "front")
    return PrematureRecastDecisionContext(
        time_seconds=time_seconds,
        bar="front",
        candidate=slot,
        slot=slot,
        next_due=tuple(next_due),
        rules=(RotationRecastRule("Long Buff", 10.0, bar="front"),),
        next_decision_time_seconds=next_decision,
        next_hard_boundary_time_seconds=hard_boundary,
        plan_end_seconds=plan_end,
    )


def test_due_required_heavy_reserves_channel_across_soft_skill_decision() -> None:
    provider = RuntimeHealerWaitDecisionProvider(
        incentives=(_incentive(),),
        required_window_seconds=1.8,
    )

    decision = provider(_context(next_decision=3.0, hard_boundary=5.0))

    assert decision is not None
    assert decision.action.kind is RotationActionKind.HEAVY_ATTACK
    assert decision.action.bar == "front"
    assert decision.action.time_seconds == 2.0
    assert decision.reservation_seconds == 1.8


def test_due_required_heavy_is_rejected_when_hard_boundary_cuts_channel_short() -> None:
    provider = RuntimeHealerWaitDecisionProvider(
        incentives=(_incentive(),),
        required_window_seconds=1.8,
    )

    decision = provider(_context(next_decision=3.0, hard_boundary=3.0))

    assert decision is None


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

    decision = provider(_context())

    assert decision is None


def test_due_required_heavy_is_rejected_when_refresh_lands_inside_channel() -> None:
    provider = RuntimeHealerWaitDecisionProvider(
        incentives=(_incentive(),),
        required_window_seconds=1.8,
    )

    decision = provider(
        _context(
            next_due=(("combat prayer", "front", 3.2),),
        )
    )

    assert decision is None


def test_scheduled_heavy_records_completion_trigger_for_later_wait_points() -> None:
    provider = RuntimeHealerWaitDecisionProvider(
        incentives=(_incentive(),),
        required_window_seconds=1.8,
    )

    first = provider(
        _context(
            time_seconds=2.0,
            next_decision=3.0,
            hard_boundary=6.0,
        )
    )
    too_soon = provider(
        _context(
            time_seconds=10.0,
            next_decision=11.0,
            hard_boundary=15.0,
        )
    )
    due_again = provider(
        _context(
            time_seconds=25.8,
            next_decision=26.0,
            hard_boundary=30.0,
        )
    )

    assert first is not None
    assert provider.runtime_states[0].last_trigger_seconds == 27.6
    assert too_soon is None
    assert due_again is not None
