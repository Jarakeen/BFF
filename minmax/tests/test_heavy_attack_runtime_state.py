import pytest

from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from minmax.heavy_attack_runtime_state import (
    HeavyAttackEffectRuntimeState,
    evaluate_required_heavy_attack_due_state,
)


def _ro_incentive() -> HealerHeavyAttackBuildIncentive:
    return HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Roaring Opportunist",
        source="verified fixture",
        recurrence_seconds=22.0,
        maximum_effect_duration_seconds=12.0,
    )


def test_required_heavy_is_due_before_first_qualifying_trigger() -> None:
    state = evaluate_required_heavy_attack_due_state(
        incentive=_ro_incentive(),
        current_time_seconds=8.0,
    )

    assert state.due is True
    assert state.next_eligible_seconds == 8.0
    assert state.effect_expires_seconds is None
    assert state.seconds_until_due == 0.0


def test_ro_due_state_preserves_effect_expiry_and_target_lockout_gap() -> None:
    state = evaluate_required_heavy_attack_due_state(
        incentive=_ro_incentive(),
        current_time_seconds=20.0,
        runtime=HeavyAttackEffectRuntimeState(
            incentive_name="Roaring Opportunist",
            bar="front",
            last_trigger_seconds=5.0,
        ),
    )

    assert state.due is False
    assert state.effect_expires_seconds == 17.0
    assert state.next_eligible_seconds == 27.0
    assert state.seconds_until_due == 7.0


def test_ro_due_state_prefers_build_effective_duration_without_changing_lockout() -> None:
    incentive = HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Roaring Opportunist",
        source="verified fixture",
        recurrence_seconds=22.0,
        maximum_effect_duration_seconds=12.0,
        effective_effect_duration_seconds=16.8,
    )

    state = evaluate_required_heavy_attack_due_state(
        incentive=incentive,
        current_time_seconds=20.0,
        runtime=HeavyAttackEffectRuntimeState(
            incentive_name="Roaring Opportunist",
            bar="front",
            last_trigger_seconds=5.0,
        ),
    )

    assert state.due is False
    assert state.effect_expires_seconds == pytest.approx(21.8)
    assert state.next_eligible_seconds == pytest.approx(27.0)
    assert state.seconds_until_due == pytest.approx(7.0)
    assert incentive.maximum_effect_duration_seconds == pytest.approx(12.0)


def test_ro_required_heavy_becomes_due_when_lockout_clears() -> None:
    state = evaluate_required_heavy_attack_due_state(
        incentive=_ro_incentive(),
        current_time_seconds=27.0,
        runtime=HeavyAttackEffectRuntimeState(
            incentive_name="Roaring Opportunist",
            bar="front",
            last_trigger_seconds=5.0,
        ),
    )

    assert state.due is True
    assert state.next_eligible_seconds == 27.0
    assert state.seconds_until_due == 0.0


def test_due_state_rejects_runtime_for_different_effect_or_bar() -> None:
    incentive = _ro_incentive()

    with pytest.raises(ValueError, match="does not match static incentive"):
        evaluate_required_heavy_attack_due_state(
            incentive=incentive,
            current_time_seconds=30.0,
            runtime=HeavyAttackEffectRuntimeState(
                incentive_name="Different Set",
                bar="front",
                last_trigger_seconds=5.0,
            ),
        )

    with pytest.raises(ValueError, match="bar does not match"):
        evaluate_required_heavy_attack_due_state(
            incentive=incentive,
            current_time_seconds=30.0,
            runtime=HeavyAttackEffectRuntimeState(
                incentive_name="Roaring Opportunist",
                bar="back",
                last_trigger_seconds=5.0,
            ),
        )


def test_due_state_rejects_non_required_or_unversioned_incentive() -> None:
    with pytest.raises(ValueError, match="required-effect"):
        evaluate_required_heavy_attack_due_state(
            incentive=HealerHeavyAttackBuildIncentive(
                bar="front",
                weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
                kind=HeavyAttackBuildIncentiveKind.RECOVERY_VALUE,
                name="Cycle of Life",
                source="fixture",
            ),
            current_time_seconds=0.0,
        )

    with pytest.raises(ValueError, match="no verified recurrence"):
        evaluate_required_heavy_attack_due_state(
            incentive=HealerHeavyAttackBuildIncentive(
                bar="front",
                weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
                kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
                name="Future Set",
                source="fixture",
            ),
            current_time_seconds=0.0,
        )
