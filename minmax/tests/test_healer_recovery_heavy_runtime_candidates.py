from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from minmax.healer_heavy_attack_runtime_candidates import HeavyAttackDecisionWindow
from minmax.healer_recovery_heavy_pressure import HealerRecoveryHeavyPressure
from minmax.healer_recovery_heavy_runtime_candidates import build_recovery_heavy_attack_candidate
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.resource_costs import ResourceType


def _incentive(bar="front") -> HealerHeavyAttackBuildIncentive:
    return HealerHeavyAttackBuildIncentive(
        bar=bar,
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.RECOVERY_VALUE,
        name="Cycle of Life",
        source="verified test evidence",
    )


def _window(bar="front") -> HeavyAttackDecisionWindow:
    return HeavyAttackDecisionWindow(
        time_seconds=4.0,
        bar=bar,
        available_window_seconds=2.0,
        required_window_seconds=1.8,
    )


def _pressure(*, recommended=True, current=2500, shortfall=0) -> HealerRecoveryHeavyPressure:
    return HealerRecoveryHeavyPressure(
        resource=ResourceType.MAGICKA,
        time_seconds=4.0,
        current_amount=current,
        maximum_amount=10000,
        resource_fraction=current / 10000,
        trigger_fraction=0.30,
        reserve_shortfall=shortfall,
        recommended=recommended,
        reason="verified pressure",
    )


def test_recovery_pressure_builds_standard_heavy_candidate() -> None:
    candidate = build_recovery_heavy_attack_candidate(
        incentive=_incentive(),
        pressure=_pressure(),
        window=_window(),
    )

    assert candidate is not None
    assert candidate.bar == "front"
    assert candidate.evidence.current_resource == 2500.0
    assert candidate.evidence.maximum_resource == 10000.0
    assert candidate.evidence.reserve_shortfall == 0


def test_verified_reserve_shortfall_is_preserved_in_candidate_evidence() -> None:
    candidate = build_recovery_heavy_attack_candidate(
        incentive=_incentive(),
        pressure=_pressure(current=7000, shortfall=1800),
        window=_window(),
    )

    assert candidate is not None
    assert candidate.evidence.current_resource == 7000.0
    assert candidate.evidence.reserve_shortfall == 1800


def test_no_recovery_pressure_produces_no_candidate() -> None:
    candidate = build_recovery_heavy_attack_candidate(
        incentive=_incentive(),
        pressure=_pressure(recommended=False, current=7000),
        window=_window(),
    )

    assert candidate is None


def test_recovery_candidate_does_not_cross_to_other_bar() -> None:
    candidate = build_recovery_heavy_attack_candidate(
        incentive=_incentive(bar="front"),
        pressure=_pressure(),
        window=_window(bar="back"),
    )

    assert candidate is None
