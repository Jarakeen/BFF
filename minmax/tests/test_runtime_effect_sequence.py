from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_eligibility import RuntimeCooldownScope, RuntimeEffectState
from minmax.runtime_effect_sequence import (
    RuntimeEffectEventAttempt,
    order_runtime_effect_attempts,
    process_effect_variant_runtime_sequence,
)
from minmax.runtime_event import RuntimeEvent


def _effect(**overrides):
    values = {
        "name": "test_effect",
        "layer": EffectLayer.PROC,
        "source": "Test Effect",
        "trigger": "damage_dealt",
    }
    values.update(overrides)
    return EffectVariant(**values)


def _attempt(time_seconds, *, sequence=0, target=None, trigger="damage_dealt", roll=None):
    return RuntimeEffectEventAttempt(
        event=RuntimeEvent(
            time_seconds=time_seconds,
            trigger=trigger,
            source="Test Event",
            target=target,
            sequence=sequence,
        ),
        chance_roll=roll,
    )


def test_attempt_ordering_uses_event_time_then_sequence():
    attempts = (
        _attempt(5.0, sequence=2),
        _attempt(3.0, sequence=9),
        _attempt(5.0, sequence=1),
    )
    ordered = order_runtime_effect_attempts(attempts)
    assert [(item.event.time_seconds, item.event.sequence) for item in ordered] == [
        (3.0, 9),
        (5.0, 1),
        (5.0, 2),
    ]


def test_sequence_carries_global_cooldown_state_forward():
    result = process_effect_variant_runtime_sequence(
        (_attempt(1.0), _attempt(5.0), _attempt(11.0)),
        _effect(cooldown=10.0),
    )
    assert [step.activation.activated for step in result.steps] == [True, False, True]
    assert result.steps[1].activation.eligibility.reasons == ("cooldown_active",)
    assert result.activation_count == 2
    assert result.final_state.last_activation_time_seconds == 11.0


def test_failed_trigger_does_not_advance_state():
    result = process_effect_variant_runtime_sequence(
        (
            _attempt(1.0),
            _attempt(20.0, trigger="light_attack"),
        ),
        _effect(),
    )
    assert result.activation_count == 1
    assert result.steps[1].activation.eligibility.reasons == ("trigger_mismatch",)
    assert result.final_state.last_activation_time_seconds == 1.0


def test_chance_roll_stays_attached_to_attempt_after_sorting():
    result = process_effect_variant_runtime_sequence(
        (
            _attempt(10.0, roll=0.9),
            _attempt(1.0, roll=0.1),
        ),
        _effect(chance=0.5),
    )
    assert [step.attempt.chance_roll for step in result.steps] == [0.1, 0.9]
    assert [step.activation.activated for step in result.steps] == [True, False]
    assert result.steps[1].activation.eligibility.reasons == ("chance_failed",)
    assert result.final_state.last_activation_time_seconds == 1.0


def test_missing_chance_roll_is_auditable_and_does_not_advance_state():
    result = process_effect_variant_runtime_sequence(
        (_attempt(1.0),),
        _effect(chance=0.25),
    )
    assert result.activation_count == 0
    assert result.steps[0].activation.eligibility.reasons == ("chance_roll_required",)
    assert result.final_state == RuntimeEffectState()


def test_target_scoped_sequence_tracks_targets_independently():
    result = process_effect_variant_runtime_sequence(
        (
            _attempt(1.0, target="ally-a"),
            _attempt(2.0, target="ally-b"),
            _attempt(5.0, target="ally-a"),
            _attempt(12.0, target="ally-a"),
        ),
        _effect(cooldown=10.0),
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    assert [step.activation.activated for step in result.steps] == [True, True, False, True]
    assert result.activation_count == 3
    assert result.final_state.last_activation_for_target("ally-a") == 12.0
    assert result.final_state.last_activation_for_target("ally-b") == 2.0
    assert result.final_state.last_activation_time_seconds is None


def test_initial_state_participates_in_sequence_cooldown():
    result = process_effect_variant_runtime_sequence(
        (_attempt(5.0), _attempt(12.0)),
        _effect(cooldown=10.0),
        initial_state=RuntimeEffectState(last_activation_time_seconds=2.0),
    )
    assert [step.activation.activated for step in result.steps] == [False, True]
    assert result.steps[0].activation.eligibility.cooldown_ready_at_seconds == 12.0
    assert result.final_state.last_activation_time_seconds == 12.0


def test_empty_sequence_preserves_initial_state():
    initial = RuntimeEffectState(last_activation_time_seconds=7.0)
    result = process_effect_variant_runtime_sequence((), _effect(), initial_state=initial)
    assert result.steps == ()
    assert result.activation_count == 0
    assert result.final_state == initial
