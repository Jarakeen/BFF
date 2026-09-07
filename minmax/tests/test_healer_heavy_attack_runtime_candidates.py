from minmax.heavy_attack_opportunity import evaluate_heavy_attack_opportunity
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.heavy_attack_runtime_state import HeavyAttackEffectRuntimeState
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from minmax.healer_heavy_attack_runtime_candidates import (
    HeavyAttackDecisionWindow,
    build_required_heavy_attack_candidates,
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


def _window(**overrides) -> HeavyAttackDecisionWindow:
    values = {
        "time_seconds": 10.0,
        "bar": "front",
        "available_window_seconds": 2.0,
        "required_window_seconds": 1.8,
    }
    values.update(overrides)
    return HeavyAttackDecisionWindow(**values)


def test_first_required_heavy_builds_candidate_immediately() -> None:
    candidates = build_required_heavy_attack_candidates(
        incentives=(_ro_incentive(),),
        window=_window(),
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.bar == "front"
    assert candidate.evidence.requirement_name == "Roaring Opportunist"
    assert evaluate_heavy_attack_opportunity(candidate.evidence).recommended is True


def test_required_heavy_is_not_candidate_while_recurrence_is_locked_out() -> None:
    candidates = build_required_heavy_attack_candidates(
        incentives=(_ro_incentive(),),
        window=_window(time_seconds=20.0),
        runtime_states=(
            HeavyAttackEffectRuntimeState(
                incentive_name="Roaring Opportunist",
                bar="front",
                last_trigger_seconds=5.0,
            ),
        ),
    )

    assert candidates == ()


def test_due_required_heavy_candidate_preserves_unsafe_window_evidence() -> None:
    candidates = build_required_heavy_attack_candidates(
        incentives=(_ro_incentive(),),
        window=_window(
            time_seconds=27.0,
            encounter_allows_channel=False,
        ),
        runtime_states=(
            HeavyAttackEffectRuntimeState(
                incentive_name="Roaring Opportunist",
                bar="front",
                last_trigger_seconds=5.0,
            ),
        ),
    )

    assert len(candidates) == 1
    opportunity = evaluate_heavy_attack_opportunity(candidates[0].evidence)
    assert opportunity.recommended is False
    assert "encounter evidence" in opportunity.reason


def test_required_heavy_candidates_ignore_other_bar_and_non_required_incentives() -> None:
    recovery = HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.RECOVERY_VALUE,
        name="Cycle of Life",
        source="fixture",
    )
    back_ro = HealerHeavyAttackBuildIncentive(
        bar="back",
        weapon=HeavyAttackWeaponType.FROST_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Roaring Opportunist",
        source="fixture",
        recurrence_seconds=22.0,
        maximum_effect_duration_seconds=12.0,
    )

    assert build_required_heavy_attack_candidates(
        incentives=(recovery, back_ro),
        window=_window(bar="front"),
    ) == ()
