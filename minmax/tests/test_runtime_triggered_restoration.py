import pytest

from minmax.resource_costs import ResourceType
from minmax.runtime_event import RuntimeEvent
from minmax.runtime_triggered_restoration import (
    RuntimeTriggeredRestorationRule,
    RuntimeTriggeredRestorationState,
    apply_runtime_triggered_restoration,
)
from minmax.triggered_restoration import (
    RESTORATION_STAFF_ABSORB,
    WARDEN_NATURES_GIFT,
)


def _event(**overrides):
    values = {
        "time_seconds": 10.0,
        "trigger": "heal_ally",
        "source": "Runtime Test",
    }
    values.update(overrides)
    return RuntimeEvent(**values)


def test_matching_trigger_emits_existing_phase4_restore_events():
    rule = RuntimeTriggeredRestorationRule(
        source=WARDEN_NATURES_GIFT,
        trigger="heal_ally",
    )
    result = apply_runtime_triggered_restoration(_event(), rule)

    assert result.activated
    assert result.state.last_activation_time_seconds == 10.0
    assert tuple((event.resource, event.amount) for event in result.restoration_events) == (
        (ResourceType.MAGICKA, 250),
        (ResourceType.STAMINA, 250),
    )
    assert all(event.time_seconds == 10.0 for event in result.restoration_events)
    assert all(event.source == "Warden: Nature's Gift" for event in result.restoration_events)


def test_trigger_mismatch_preserves_state_and_emits_nothing():
    state = RuntimeTriggeredRestorationState(last_activation_time_seconds=5.0)
    rule = RuntimeTriggeredRestorationRule(
        source=WARDEN_NATURES_GIFT,
        trigger="heal_ally",
    )
    result = apply_runtime_triggered_restoration(
        _event(trigger="damage_dealt"),
        rule,
        state=state,
    )

    assert not result.activated
    assert result.state is state
    assert result.restoration_events == ()
    assert result.reasons == ("trigger_mismatch",)


def test_cooldown_blocks_until_exact_ready_time():
    rule = RuntimeTriggeredRestorationRule(
        source=WARDEN_NATURES_GIFT,
        trigger="heal_ally",
    )
    state = RuntimeTriggeredRestorationState(last_activation_time_seconds=10.0)

    blocked = apply_runtime_triggered_restoration(
        _event(time_seconds=10.999),
        rule,
        state=state,
    )
    ready = apply_runtime_triggered_restoration(
        _event(time_seconds=11.0),
        rule,
        state=state,
    )

    assert not blocked.activated
    assert blocked.reasons == ("cooldown_active",)
    assert blocked.cooldown_ready_at_seconds == 11.0
    assert ready.activated
    assert ready.state.last_activation_time_seconds == 11.0


def test_absorb_uses_verified_quarter_second_cooldown():
    rule = RuntimeTriggeredRestorationRule(
        source=RESTORATION_STAFF_ABSORB,
        trigger="damage_taken",
    )
    first = apply_runtime_triggered_restoration(
        _event(time_seconds=3.0, trigger="damage_taken"),
        rule,
    )
    blocked = apply_runtime_triggered_restoration(
        _event(time_seconds=3.249, trigger="damage_taken"),
        rule,
        state=first.state,
    )
    ready = apply_runtime_triggered_restoration(
        _event(time_seconds=3.25, trigger="damage_taken"),
        rule,
        state=first.state,
    )

    assert first.activated
    assert not blocked.activated
    assert ready.activated
    assert ready.restoration_events[0].resource is ResourceType.MAGICKA
    assert ready.restoration_events[0].amount == 600


def test_failed_attempt_does_not_advance_cooldown_state():
    state = RuntimeTriggeredRestorationState(last_activation_time_seconds=10.0)
    rule = RuntimeTriggeredRestorationRule(
        source=WARDEN_NATURES_GIFT,
        trigger="heal_ally",
    )
    result = apply_runtime_triggered_restoration(
        _event(time_seconds=10.5),
        rule,
        state=state,
    )

    assert not result.activated
    assert result.state is state


def test_runtime_state_rejects_invalid_timestamp():
    with pytest.raises(ValueError, match="last_activation_time_seconds"):
        RuntimeTriggeredRestorationState(last_activation_time_seconds=-1.0)


def test_rule_requires_trigger_identity():
    with pytest.raises(ValueError, match="requires a trigger"):
        RuntimeTriggeredRestorationRule(
            source=WARDEN_NATURES_GIFT,
            trigger="",
        )


def test_matching_event_cannot_move_state_backward():
    rule = RuntimeTriggeredRestorationRule(
        source=WARDEN_NATURES_GIFT,
        trigger="heal_ally",
    )
    state = RuntimeTriggeredRestorationState(last_activation_time_seconds=10.0)

    with pytest.raises(ValueError, match="backward in time"):
        apply_runtime_triggered_restoration(
            _event(time_seconds=9.0),
            rule,
            state=state,
        )
