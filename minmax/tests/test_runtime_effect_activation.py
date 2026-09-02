import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_activation import apply_effect_variant_runtime_activation
from minmax.runtime_effect_eligibility import RuntimeCooldownScope, RuntimeEffectState
from minmax.runtime_event import RuntimeEvent


def _effect(**overrides):
    values = {
        "name": "test_effect",
        "layer": EffectLayer.PROC,
        "source": "Test Source",
        "trigger": "damage_dealt",
    }
    values.update(overrides)
    return EffectVariant(**values)


def _event(**overrides):
    values = {
        "time_seconds": 10.0,
        "trigger": "damage_dealt",
        "source": "Test Event",
    }
    values.update(overrides)
    return RuntimeEvent(**values)


def test_successful_global_activation_records_timestamp():
    result = apply_effect_variant_runtime_activation(_event(), _effect())
    assert result.activated
    assert result.eligibility.eligible
    assert result.state.last_activation_time_seconds == 10.0
    assert result.state.target_last_activation_times == ()


def test_failed_activation_leaves_state_unchanged():
    state = RuntimeEffectState(last_activation_time_seconds=4.0)
    result = apply_effect_variant_runtime_activation(
        _event(trigger="light_attack"),
        _effect(),
        state=state,
    )
    assert not result.activated
    assert result.eligibility.reasons == ("trigger_mismatch",)
    assert result.state is state


def test_successful_activation_then_cooldown_blocks_followup():
    effect = _effect(cooldown=10.0)
    first = apply_effect_variant_runtime_activation(
        _event(time_seconds=5.0),
        effect,
    )
    second = apply_effect_variant_runtime_activation(
        _event(time_seconds=12.0),
        effect,
        state=first.state,
    )
    assert first.activated
    assert not second.activated
    assert second.eligibility.reasons == ("cooldown_active",)
    assert second.eligibility.cooldown_ready_at_seconds == 15.0
    assert second.state == first.state


def test_global_activation_at_ready_time_advances_state():
    effect = _effect(cooldown=10.0)
    state = RuntimeEffectState(last_activation_time_seconds=5.0)
    result = apply_effect_variant_runtime_activation(
        _event(time_seconds=15.0),
        effect,
        state=state,
    )
    assert result.activated
    assert result.state.last_activation_time_seconds == 15.0


def test_target_scoped_activation_records_only_matching_target():
    state = RuntimeEffectState(
        last_activation_time_seconds=3.0,
        target_last_activation_times=(("ally-b", 2.0),),
    )
    result = apply_effect_variant_runtime_activation(
        _event(time_seconds=10.0, target="ally-a"),
        _effect(cooldown=30.0),
        state=state,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    assert result.activated
    assert result.state.last_activation_time_seconds == 3.0
    assert result.state.target_last_activation_times == (
        ("ally-a", 10.0),
        ("ally-b", 2.0),
    )


def test_target_cooldown_history_is_independent_per_target():
    effect = _effect(cooldown=30.0)
    first = apply_effect_variant_runtime_activation(
        _event(time_seconds=10.0, target="ally-a"),
        effect,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    other_target = apply_effect_variant_runtime_activation(
        _event(time_seconds=11.0, target="ally-b"),
        effect,
        state=first.state,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    same_target = apply_effect_variant_runtime_activation(
        _event(time_seconds=12.0, target="ally-a"),
        effect,
        state=other_target.state,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    assert first.activated
    assert other_target.activated
    assert not same_target.activated
    assert same_target.eligibility.reasons == ("cooldown_active",)
    assert same_target.eligibility.cooldown_ready_at_seconds == 40.0


def test_failed_chance_does_not_start_cooldown():
    effect = _effect(chance=0.25, cooldown=10.0)
    failed = apply_effect_variant_runtime_activation(
        _event(time_seconds=5.0),
        effect,
        chance_roll=0.5,
    )
    passed = apply_effect_variant_runtime_activation(
        _event(time_seconds=6.0),
        effect,
        state=failed.state,
        chance_roll=0.1,
    )
    assert not failed.activated
    assert failed.state.last_activation_time_seconds is None
    assert passed.activated
    assert passed.state.last_activation_time_seconds == 6.0


def test_global_activation_rejects_moving_state_backward():
    with pytest.raises(ValueError, match="backward"):
        apply_effect_variant_runtime_activation(
            _event(time_seconds=9.0),
            _effect(),
            state=RuntimeEffectState(last_activation_time_seconds=10.0),
        )


def test_target_activation_rejects_moving_target_state_backward():
    with pytest.raises(ValueError, match="backward"):
        apply_effect_variant_runtime_activation(
            _event(time_seconds=9.0, target="ally-a"),
            _effect(),
            state=RuntimeEffectState(target_last_activation_times=(("ally-a", 10.0),)),
            cooldown_scope=RuntimeCooldownScope.TARGET,
        )


def test_target_scoped_activation_without_target_is_rejected_even_without_cooldown():
    with pytest.raises(ValueError, match="target identity"):
        apply_effect_variant_runtime_activation(
            _event(),
            _effect(),
            cooldown_scope=RuntimeCooldownScope.TARGET,
        )
