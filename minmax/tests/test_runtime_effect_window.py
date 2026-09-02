import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_activation import apply_effect_variant_runtime_activation
from minmax.runtime_effect_window import (
    RuntimeEffectActiveWindow,
    active_window_from_effect_activation,
    order_runtime_effect_windows,
    partition_runtime_effect_windows,
)
from minmax.runtime_event import RuntimeEvent


def _effect(**overrides):
    values = {
        "name": "test_effect",
        "layer": EffectLayer.PROC,
        "source": "Test Source",
        "trigger": "damage_dealt",
        "duration": 5.0,
    }
    values.update(overrides)
    return EffectVariant(**values)


def _event(**overrides):
    values = {
        "time_seconds": 10.0,
        "trigger": "damage_dealt",
        "source": "Test Event",
        "sequence": 2,
    }
    values.update(overrides)
    return RuntimeEvent(**values)


def _successful_activation(event=None, effect=None):
    event = event or _event()
    effect = effect or _effect()
    return event, effect, apply_effect_variant_runtime_activation(event, effect)


def test_successful_activation_creates_explicit_duration_window():
    event, effect, activation = _successful_activation()
    window = active_window_from_effect_activation(event, effect, activation)

    assert window is not None
    assert window.effect_name == "test_effect"
    assert window.source == "Test Source"
    assert window.start_time_seconds == 10.0
    assert window.end_time_seconds == 15.0
    assert window.duration_seconds == 5.0
    assert window.sequence == 2


def test_failed_activation_does_not_create_active_window():
    event = _event(trigger="light_attack")
    effect = _effect()
    activation = apply_effect_variant_runtime_activation(event, effect)

    assert not activation.activated
    assert active_window_from_effect_activation(event, effect, activation) is None


def test_missing_or_zero_duration_does_not_invent_window():
    for duration in (None, 0.0):
        event = _event()
        effect = _effect(duration=duration)
        activation = apply_effect_variant_runtime_activation(event, effect)
        assert activation.activated
        assert active_window_from_effect_activation(event, effect, activation) is None


def test_invalid_runtime_duration_is_rejected():
    event = _event()
    effect = _effect(duration=-1.0)
    activation = apply_effect_variant_runtime_activation(event, effect)

    with pytest.raises(ValueError, match="duration"):
        active_window_from_effect_activation(event, effect, activation)


def test_window_is_active_at_start_and_inactive_at_exact_expiration():
    window = RuntimeEffectActiveWindow(
        effect_name="major_slayer",
        source="Test",
        start_time_seconds=10.0,
        end_time_seconds=15.0,
    )

    assert window.is_active_at(10.0)
    assert window.is_active_at(14.999)
    assert not window.is_active_at(15.0)


def test_partition_separates_active_and_expired_and_omits_future_windows():
    expired = RuntimeEffectActiveWindow(
        effect_name="expired",
        source="Test",
        start_time_seconds=1.0,
        end_time_seconds=3.0,
    )
    active = RuntimeEffectActiveWindow(
        effect_name="active",
        source="Test",
        start_time_seconds=4.0,
        end_time_seconds=8.0,
    )
    future = RuntimeEffectActiveWindow(
        effect_name="future",
        source="Test",
        start_time_seconds=7.0,
        end_time_seconds=9.0,
    )

    result = partition_runtime_effect_windows(
        (future, active, expired),
        at_time_seconds=6.0,
    )

    assert result.active == (active,)
    assert result.expired == (expired,)


def test_ordering_is_deterministic_for_same_start_time():
    later_sequence = RuntimeEffectActiveWindow(
        effect_name="zeta",
        source="B",
        start_time_seconds=5.0,
        end_time_seconds=8.0,
        sequence=2,
    )
    earlier_sequence = RuntimeEffectActiveWindow(
        effect_name="alpha",
        source="A",
        start_time_seconds=5.0,
        end_time_seconds=8.0,
        sequence=1,
    )

    assert order_runtime_effect_windows((later_sequence, earlier_sequence)) == (
        earlier_sequence,
        later_sequence,
    )


def test_invalid_window_bounds_are_rejected():
    with pytest.raises(ValueError, match="after its start"):
        RuntimeEffectActiveWindow(
            effect_name="test",
            source="Test",
            start_time_seconds=5.0,
            end_time_seconds=5.0,
        )


def test_partition_rejects_invalid_query_time():
    window = RuntimeEffectActiveWindow(
        effect_name="test",
        source="Test",
        start_time_seconds=1.0,
        end_time_seconds=2.0,
    )
    with pytest.raises(ValueError, match="query time"):
        partition_runtime_effect_windows((window,), at_time_seconds=-1.0)
