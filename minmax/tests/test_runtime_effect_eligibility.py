import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_eligibility import (
    RuntimeCooldownScope,
    RuntimeEffectState,
    evaluate_effect_variant_runtime_eligibility,
)
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


def test_matching_unconditional_effect_is_runtime_eligible():
    result = evaluate_effect_variant_runtime_eligibility(_event(), _effect())
    assert result.eligible
    assert result.reasons == ()


def test_trigger_mismatch_is_explicit():
    result = evaluate_effect_variant_runtime_eligibility(
        _event(trigger="light_attack"),
        _effect(),
    )
    assert not result.eligible
    assert result.reasons == ("trigger_mismatch",)


def test_static_ineligibility_remains_authoritative():
    result = evaluate_effect_variant_runtime_eligibility(
        _event(),
        _effect(eligible=False),
    )
    assert not result.eligible
    assert result.reasons == ("effect_not_statically_eligible",)


def test_global_cooldown_blocks_until_ready_time():
    result = evaluate_effect_variant_runtime_eligibility(
        _event(time_seconds=20.0),
        _effect(cooldown=10.0),
        state=RuntimeEffectState(last_activation_time_seconds=15.0),
    )
    assert not result.eligible
    assert result.reasons == ("cooldown_active",)
    assert result.cooldown_ready_at_seconds == 25.0


def test_global_cooldown_allows_event_at_exact_ready_time():
    result = evaluate_effect_variant_runtime_eligibility(
        _event(time_seconds=25.0),
        _effect(cooldown=10.0),
        state=RuntimeEffectState(last_activation_time_seconds=15.0),
    )
    assert result.eligible
    assert result.cooldown_ready_at_seconds == 25.0


def test_per_target_cooldown_uses_only_matching_target_state():
    state = RuntimeEffectState(
        target_last_activation_times=(("ally-a", 15.0), ("ally-b", 2.0)),
    )
    blocked = evaluate_effect_variant_runtime_eligibility(
        _event(time_seconds=20.0, target="ally-a"),
        _effect(cooldown=10.0),
        state=state,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    ready = evaluate_effect_variant_runtime_eligibility(
        _event(time_seconds=20.0, target="ally-b"),
        _effect(cooldown=10.0),
        state=state,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    assert not blocked.eligible
    assert blocked.reasons == ("cooldown_active",)
    assert ready.eligible


def test_per_target_cooldown_requires_target_identity():
    result = evaluate_effect_variant_runtime_eligibility(
        _event(),
        _effect(cooldown=10.0),
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    assert not result.eligible
    assert result.reasons == ("target_identity_required_for_cooldown",)


def test_chance_requires_caller_supplied_deterministic_roll():
    result = evaluate_effect_variant_runtime_eligibility(
        _event(),
        _effect(chance=0.25),
    )
    assert not result.eligible
    assert result.chance_roll_required
    assert result.reasons == ("chance_roll_required",)


def test_chance_roll_below_probability_passes_and_equal_probability_fails():
    passed = evaluate_effect_variant_runtime_eligibility(
        _event(),
        _effect(chance=0.25),
        chance_roll=0.249,
    )
    failed = evaluate_effect_variant_runtime_eligibility(
        _event(),
        _effect(chance=0.25),
        chance_roll=0.25,
    )
    assert passed.eligible
    assert not failed.eligible
    assert failed.reasons == ("chance_failed",)


def test_invalid_chance_roll_is_rejected():
    with pytest.raises(ValueError, match="chance_roll"):
        evaluate_effect_variant_runtime_eligibility(
            _event(),
            _effect(chance=0.5),
            chance_roll=1.1,
        )


def test_runtime_state_rejects_duplicate_target_cooldown_entries():
    with pytest.raises(ValueError, match="duplicate target cooldown"):
        RuntimeEffectState(
            target_last_activation_times=(("ally", 1.0), ("ally", 2.0)),
        )
