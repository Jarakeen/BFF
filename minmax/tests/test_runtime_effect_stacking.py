import pytest

from minmax.runtime_effect_stacking import (
    apply_runtime_effect_window_stacking,
    effective_runtime_effect_windows,
)
from minmax.runtime_effect_window import RuntimeEffectActiveWindow
from minmax.support_stacking import StackingBehavior


def _window(**overrides):
    values = {
        "effect_name": "major_slayer",
        "source": "Test Source",
        "start_time_seconds": 1.0,
        "end_time_seconds": 11.0,
        "magnitude": 10.0,
    }
    values.update(overrides)
    return RuntimeEffectActiveWindow(**values)


def test_missing_stacking_behavior_remains_explicitly_unresolved():
    existing = _window()
    new = _window(source="New", start_time_seconds=5.0, end_time_seconds=10.0)

    result = apply_runtime_effect_window_stacking((existing,), new, behavior=None)

    assert not result.resolved
    assert result.retained == (existing,)
    assert result.unresolved == ("stacking_behavior_required",)


def test_stacks_retains_overlapping_applications():
    first = _window(source="A", sequence=1)
    second = _window(source="B", start_time_seconds=2.0, end_time_seconds=12.0, sequence=2)

    result = apply_runtime_effect_window_stacking(
        (first,),
        second,
        behavior=StackingBehavior.STACKS,
    )

    assert result.resolved
    assert result.retained == (first, second)
    assert result.superseded == ()


def test_unique_refresh_truncates_older_overlapping_window():
    first = _window(source="A", start_time_seconds=1.0, end_time_seconds=11.0)
    second = _window(source="B", start_time_seconds=5.0, end_time_seconds=10.0)

    result = apply_runtime_effect_window_stacking(
        (first,),
        second,
        behavior=StackingBehavior.UNIQUE,
    )

    assert result.resolved
    assert len(result.retained) == 2
    truncated, current = result.retained
    assert truncated.source == "A"
    assert truncated.end_time_seconds == 5.0
    assert current == second
    assert result.superseded == (first,)


def test_unique_refresh_does_not_replace_same_effect_on_different_target():
    ally_a = _window(target="ally-a")
    ally_b = _window(source="B", target="ally-b", start_time_seconds=5.0, end_time_seconds=10.0)

    result = apply_runtime_effect_window_stacking(
        (ally_a,),
        ally_b,
        behavior=StackingBehavior.UNIQUE,
    )

    assert result.retained == (ally_a, ally_b)
    assert result.superseded == ()


def test_unique_preserves_expired_history_without_truncating_it():
    expired = _window(end_time_seconds=3.0)
    new = _window(source="New", start_time_seconds=5.0, end_time_seconds=10.0)

    result = apply_runtime_effect_window_stacking(
        (expired,),
        new,
        behavior=StackingBehavior.UNIQUE,
    )

    assert result.retained == (expired, new)
    assert result.superseded == ()


def test_unique_rejects_out_of_order_overlapping_application():
    future_existing = _window(start_time_seconds=8.0, end_time_seconds=12.0)
    earlier_new = _window(source="Earlier", start_time_seconds=5.0, end_time_seconds=10.0)

    with pytest.raises(ValueError, match="chronological order"):
        apply_runtime_effect_window_stacking(
            (future_existing,),
            earlier_new,
            behavior=StackingBehavior.UNIQUE,
        )


def test_highest_only_requires_magnitude_when_comparison_is_needed():
    unknown = _window(magnitude=None)
    known = _window(source="Known", start_time_seconds=2.0, end_time_seconds=8.0, magnitude=20.0)

    result = apply_runtime_effect_window_stacking(
        (unknown,),
        known,
        behavior=StackingBehavior.HIGHEST_ONLY,
    )

    assert not result.resolved
    assert result.retained == (unknown,)
    assert result.unresolved == ("magnitude_required_for_highest_only",)


def test_highest_only_retains_weaker_window_for_later_fallback():
    weaker = _window(source="Weak", magnitude=10.0, end_time_seconds=20.0)
    stronger = _window(
        source="Strong",
        start_time_seconds=5.0,
        end_time_seconds=10.0,
        magnitude=20.0,
    )

    applied = apply_runtime_effect_window_stacking(
        (weaker,),
        stronger,
        behavior=StackingBehavior.HIGHEST_ONLY,
    )
    during = effective_runtime_effect_windows(
        applied.retained,
        behavior=StackingBehavior.HIGHEST_ONLY,
        at_time_seconds=7.0,
    )
    after = effective_runtime_effect_windows(
        applied.retained,
        behavior=StackingBehavior.HIGHEST_ONLY,
        at_time_seconds=12.0,
    )

    assert applied.retained == (weaker, stronger)
    assert during.retained == (stronger,)
    assert during.superseded == (weaker,)
    assert after.retained == (weaker,)


def test_highest_only_uses_effect_name_and_target_as_comparison_scope():
    slayer = _window(effect_name="major_slayer", target="ally", magnitude=10.0)
    courage = _window(
        effect_name="major_courage",
        source="Courage",
        target="ally",
        magnitude=100.0,
    )

    result = effective_runtime_effect_windows(
        (slayer, courage),
        behavior=StackingBehavior.HIGHEST_ONLY,
        at_time_seconds=5.0,
    )

    assert result.retained == (slayer, courage)
    assert result.superseded == ()


def test_highest_only_equal_magnitudes_choose_deterministic_representative():
    earlier = _window(source="A", start_time_seconds=1.0, sequence=1, magnitude=10.0)
    later = _window(source="B", start_time_seconds=2.0, end_time_seconds=9.0, sequence=2, magnitude=10.0)

    result = effective_runtime_effect_windows(
        (later, earlier),
        behavior=StackingBehavior.HIGHEST_ONLY,
        at_time_seconds=5.0,
    )

    assert result.retained == (later,)
    assert result.superseded == (earlier,)


def test_window_created_from_effect_can_preserve_magnitude_for_stacking():
    window = _window(magnitude=123.5)
    assert window.magnitude == 123.5
