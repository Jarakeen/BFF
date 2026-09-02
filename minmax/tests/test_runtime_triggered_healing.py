import pytest

from minmax.runtime_event import RuntimeEvent
from minmax.runtime_triggered_healing import (
    RuntimeTriggeredHealingRule,
    RuntimeTriggeredHealingState,
    apply_runtime_triggered_healing,
)
from minmax.triggered_healing import TriggeredHealingEvent


def _event(**overrides):
    values = {
        "time_seconds": 10.0,
        "trigger": "damage_dealt",
        "source": "Test Event",
        "target": "ally-a",
    }
    values.update(overrides)
    return RuntimeEvent(**values)


def _rule(**overrides):
    values = {
        "source": "Secondary Heal",
        "trigger": "damage_dealt",
        "cooldown_seconds": 1.0,
    }
    values.update(overrides)
    return RuntimeTriggeredHealingRule(**values)


def test_matching_trigger_emits_caller_resolved_healing_event():
    result = apply_runtime_triggered_healing(
        _event(),
        _rule(),
        amount=1234.5,
    )

    assert result.activated
    assert result.healing_event == TriggeredHealingEvent(
        time_seconds=10.0,
        amount=1234.5,
        source="Secondary Heal",
        target="ally-a",
    )
    assert result.state.last_activation_time_seconds == 10.0


def test_trigger_mismatch_does_not_advance_state():
    state = RuntimeTriggeredHealingState(last_activation_time_seconds=5.0)
    result = apply_runtime_triggered_healing(
        _event(trigger="light_attack"),
        _rule(),
        amount=100.0,
        state=state,
    )

    assert not result.activated
    assert result.state is state
    assert result.healing_event is None
    assert result.reasons == ("trigger_mismatch",)


def test_missing_target_is_explicit_and_does_not_advance_state():
    state = RuntimeTriggeredHealingState(last_activation_time_seconds=5.0)
    result = apply_runtime_triggered_healing(
        _event(target=None),
        _rule(),
        amount=100.0,
        state=state,
    )

    assert not result.activated
    assert result.state is state
    assert result.reasons == ("target_identity_required",)


def test_explicit_target_can_override_event_target():
    result = apply_runtime_triggered_healing(
        _event(target="enemy-source"),
        _rule(),
        amount=100.0,
        target="self",
    )

    assert result.activated
    assert result.healing_event is not None
    assert result.healing_event.target == "self"


def test_cooldown_blocks_without_advancing_state():
    state = RuntimeTriggeredHealingState(last_activation_time_seconds=9.5)
    result = apply_runtime_triggered_healing(
        _event(time_seconds=10.0),
        _rule(cooldown_seconds=1.0),
        amount=100.0,
        state=state,
    )

    assert not result.activated
    assert result.state is state
    assert result.reasons == ("cooldown_active",)
    assert result.cooldown_ready_at_seconds == 10.5


def test_exact_cooldown_ready_time_activates():
    state = RuntimeTriggeredHealingState(last_activation_time_seconds=9.0)
    result = apply_runtime_triggered_healing(
        _event(time_seconds=10.0),
        _rule(cooldown_seconds=1.0),
        amount=100.0,
        state=state,
    )

    assert result.activated
    assert result.state.last_activation_time_seconds == 10.0
    assert result.cooldown_ready_at_seconds == 10.0


def test_invalid_amount_is_rejected_without_interpreting_healing_math():
    with pytest.raises(ValueError, match="amount"):
        apply_runtime_triggered_healing(
            _event(),
            _rule(),
            amount=-1.0,
        )


def test_successful_runtime_healing_cannot_move_state_backward():
    state = RuntimeTriggeredHealingState(last_activation_time_seconds=11.0)
    with pytest.raises(ValueError, match="backward"):
        apply_runtime_triggered_healing(
            _event(time_seconds=10.0),
            _rule(cooldown_seconds=0.0),
            amount=100.0,
            state=state,
        )
