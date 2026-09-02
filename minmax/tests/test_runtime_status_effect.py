import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_eligibility import RuntimeCooldownScope
from minmax.runtime_effect_runtime import RuntimeEffectRuntimeState
from minmax.runtime_event import RuntimeEvent
from minmax.runtime_status_effect import (
    active_status_targets,
    apply_runtime_status_event,
    status_active_on_target,
)
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior


def _status(**overrides):
    values = {
        "name": "chilled",
        "layer": EffectLayer.PROC,
        "source": "Frost Damage",
        "trigger": "damage_dealt",
        "category": SupportEffectCategory.STATUS,
        "duration": 4.0,
        "stacking": StackingBehavior.UNIQUE,
    }
    values.update(overrides)
    return EffectVariant(**values)


def _event(**overrides):
    values = {
        "time_seconds": 10.0,
        "trigger": "damage_dealt",
        "source": "Frost Hit",
        "target": "boss",
    }
    values.update(overrides)
    return RuntimeEvent(**values)


def test_status_application_creates_target_scoped_active_window():
    result = apply_runtime_status_event(_event(), _status())

    assert result.applied
    assert result.resolved
    assert status_active_on_target(result.state, target="boss", at_time_seconds=10.0)
    assert status_active_on_target(result.state, target="boss", at_time_seconds=13.999)
    assert not status_active_on_target(result.state, target="boss", at_time_seconds=14.0)


def test_status_query_does_not_leak_between_targets():
    first = apply_runtime_status_event(_event(target="boss-a"), _status())
    second = apply_runtime_status_event(
        _event(time_seconds=11.0, target="boss-b"),
        _status(),
        state=first.state,
    )

    assert status_active_on_target(second.state, target="boss-a", at_time_seconds=12.0)
    assert status_active_on_target(second.state, target="boss-b", at_time_seconds=12.0)
    assert active_status_targets(second.state, at_time_seconds=12.0) == ("boss-a", "boss-b")


def test_status_refresh_uses_existing_unique_window_semantics():
    first = apply_runtime_status_event(_event(time_seconds=1.0), _status(duration=5.0))
    refreshed = apply_runtime_status_event(
        _event(time_seconds=3.0),
        _status(duration=5.0),
        state=first.state,
    )

    assert refreshed.resolved
    assert len(refreshed.state.windows) == 2
    assert refreshed.state.windows[0].end_time_seconds == 3.0
    assert refreshed.state.windows[1].end_time_seconds == 8.0


def test_failed_status_proc_does_not_create_status_truth():
    result = apply_runtime_status_event(
        _event(),
        _status(chance=0.25),
        chance_roll=0.5,
    )

    assert not result.applied
    assert not status_active_on_target(result.state, target="boss", at_time_seconds=10.0)


def test_status_without_duration_records_application_but_remains_unresolved():
    result = apply_runtime_status_event(_event(), _status(duration=None))

    assert result.applied
    assert not result.resolved
    assert result.unresolved == ("status_duration_required",)
    assert result.state.activation_state.last_activation_time_seconds == 10.0
    assert result.state.windows == ()


def test_status_runtime_rejects_non_status_effect_variant():
    effect = _status(category=SupportEffectCategory.DEBUFF)
    with pytest.raises(ValueError, match="STATUS"):
        apply_runtime_status_event(_event(), effect)


def test_status_runtime_requires_explicit_target_identity():
    with pytest.raises(ValueError, match="target identity"):
        apply_runtime_status_event(_event(target=None), _status())


def test_target_scoped_status_cooldown_reuses_canonical_runtime_state():
    effect = _status(cooldown=10.0)
    first = apply_runtime_status_event(
        _event(time_seconds=1.0, target="boss-a"),
        effect,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    blocked = apply_runtime_status_event(
        _event(time_seconds=5.0, target="boss-a"),
        effect,
        state=first.state,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    other_target = apply_runtime_status_event(
        _event(time_seconds=5.0, target="boss-b"),
        effect,
        state=first.state,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )

    assert not blocked.applied
    assert blocked.transition.activation.eligibility.reasons == ("cooldown_active",)
    assert other_target.applied


def test_status_query_rejects_invalid_time():
    with pytest.raises(ValueError, match="query time"):
        active_status_targets(RuntimeEffectRuntimeState(), at_time_seconds=-1.0)
