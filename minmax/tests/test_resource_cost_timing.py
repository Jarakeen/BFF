import pytest

from minmax.resource_cost_timing import (
    ActionCostTiming,
    CostTimingKind,
    resolve_action_cost_timing,
)


def test_non_recurring_cost_resolves_to_activation() -> None:
    timing = resolve_action_cost_timing(base_is_cost_time="false", charge_freq="0")

    assert timing == ActionCostTiming(CostTimingKind.ON_ACTIVATION)


def test_blood_frenzy_resolves_to_two_second_recurring_cost() -> None:
    timing = resolve_action_cost_timing(base_is_cost_time="true", charge_freq="2000")

    assert timing.kind is CostTimingKind.RECURRING
    assert timing.interval_seconds == 2.0


def test_banner_bearer_repeated_resource_intervals_are_collapsed() -> None:
    timing = resolve_action_cost_timing(base_is_cost_time="true", charge_freq="2000,2000")

    assert timing == ActionCostTiming(
        CostTimingKind.RECURRING,
        interval_seconds=2.0,
    )


def test_recurring_cost_rejects_missing_frequency() -> None:
    with pytest.raises(ValueError, match="missing chargeFreq"):
        resolve_action_cost_timing(base_is_cost_time="true", charge_freq="")


def test_recurring_cost_rejects_non_positive_frequency() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        resolve_action_cost_timing(base_is_cost_time=True, charge_freq="0")


def test_recurring_cost_rejects_divergent_compound_intervals() -> None:
    with pytest.raises(ValueError, match="divergent intervals"):
        resolve_action_cost_timing(base_is_cost_time=True, charge_freq="2000,3000")


def test_recurring_timing_contract_requires_positive_interval() -> None:
    with pytest.raises(ValueError, match="positive interval"):
        ActionCostTiming(CostTimingKind.RECURRING, interval_seconds=0)
