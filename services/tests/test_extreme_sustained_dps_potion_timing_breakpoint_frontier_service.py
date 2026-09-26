from __future__ import annotations

import pytest

from services.extreme_sustained_dps_potion_timing_breakpoint_frontier_service import (
    ExtremeSustainedDPSPotionTimingBreakpointFrontierService,
)


def test_breakpoint_frontier_reduces_continuous_offset_to_finite_state_regions() -> None:
    result = ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
        duration_seconds=20.0,
        cooldown_seconds=10.0,
        observation_times=(1.0, 4.0, 9.0, 12.0, 19.0),
        effective_buff_durations=(3.0,),
    )

    assert result.named_buff_state_denominator_proven is True
    assert result.full_potion_timing_closed is False
    offsets = tuple(row.first_use_seconds for row in result.choices)
    assert 0.0 in offsets
    assert 1.0 in offsets
    assert 4.0 in offsets
    assert 6.0 in offsets
    assert 9.0 in offsets
    assert any(row.kind == "open_interval_representative" for row in result.choices)
    assert result.omitted_scope == (
        "potion instant-restoration timing is not closed by named-buff breakpoint coverage",
    )


def test_breakpoints_include_expiry_boundaries_modulo_cooldown() -> None:
    result = ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
        duration_seconds=30.0,
        cooldown_seconds=10.0,
        observation_times=(8.0, 18.0, 28.0),
        effective_buff_durations=(5.0,),
    )

    offsets = tuple(row.first_use_seconds for row in result.choices)
    assert 3.0 in offsets
    assert 8.0 in offsets


def test_full_potion_timing_closes_only_when_restoration_timing_is_also_closed() -> None:
    result = ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
        duration_seconds=20.0,
        cooldown_seconds=10.0,
        observation_times=(5.0, 15.0),
        effective_buff_durations=(4.0,),
        instant_restoration_timing_closed=True,
    )

    assert result.named_buff_state_denominator_proven is True
    assert result.full_potion_timing_closed is True
    assert result.omitted_scope == ()


def test_empty_observation_set_fails_closed() -> None:
    result = ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
        duration_seconds=20.0,
        cooldown_seconds=10.0,
        observation_times=(),
        effective_buff_durations=(4.0,),
    )

    assert result.named_buff_state_denominator_proven is False
    assert result.full_potion_timing_closed is False
    assert any("observation set is empty" in row for row in result.unresolved)


def test_empty_named_buff_duration_set_fails_closed() -> None:
    result = ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
        duration_seconds=20.0,
        cooldown_seconds=10.0,
        observation_times=(5.0,),
        effective_buff_durations=(),
    )

    assert result.named_buff_state_denominator_proven is False
    assert any("No effective named-buff durations" in row for row in result.unresolved)


def test_breakpoint_frontier_requires_strict_restoration_proof_boolean() -> None:
    with pytest.raises(TypeError, match="instant_restoration_timing_closed must be boolean"):
        ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
            duration_seconds=20.0,
            cooldown_seconds=10.0,
            observation_times=(5.0,),
            effective_buff_durations=(4.0,),
            instant_restoration_timing_closed="false",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "field,value,match",
    (
        ("duration_seconds", True, "duration_seconds must be numeric"),
        ("cooldown_seconds", "10", "cooldown_seconds must be numeric"),
    ),
)
def test_breakpoint_frontier_rejects_coerced_scalar_inputs(field, value, match) -> None:
    kwargs = {
        "duration_seconds": 20.0,
        "cooldown_seconds": 10.0,
        "observation_times": (5.0,),
        "effective_buff_durations": (4.0,),
    }
    kwargs[field] = value

    with pytest.raises(TypeError, match=match):
        ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(**kwargs)


def test_breakpoint_frontier_requires_tuple_observation_and_duration_collections() -> None:
    with pytest.raises(TypeError, match="observation_times must be a tuple"):
        ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
            duration_seconds=20.0,
            cooldown_seconds=10.0,
            observation_times=[5.0],  # type: ignore[arg-type]
            effective_buff_durations=(4.0,),
        )

    with pytest.raises(TypeError, match="effective_buff_durations must be a tuple"):
        ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
            duration_seconds=20.0,
            cooldown_seconds=10.0,
            observation_times=(5.0,),
            effective_buff_durations=[4.0],  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("value", (False, "5", None))
def test_breakpoint_frontier_rejects_coerced_observation_times(value) -> None:
    with pytest.raises(TypeError, match="observation times must be numeric"):
        ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
            duration_seconds=20.0,
            cooldown_seconds=10.0,
            observation_times=(value,),  # type: ignore[arg-type]
            effective_buff_durations=(4.0,),
        )


@pytest.mark.parametrize("value", (True, "4", None))
def test_breakpoint_frontier_rejects_coerced_buff_durations(value) -> None:
    with pytest.raises(TypeError, match="buff durations must be numeric"):
        ExtremeSustainedDPSPotionTimingBreakpointFrontierService.build(
            duration_seconds=20.0,
            cooldown_seconds=10.0,
            observation_times=(5.0,),
            effective_buff_durations=(value,),  # type: ignore[arg-type]
        )
