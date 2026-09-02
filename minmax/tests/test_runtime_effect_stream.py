from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_eligibility import RuntimeCooldownScope, RuntimeEffectState
from minmax.runtime_effect_runtime import RuntimeEffectRuntimeState
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_effect_stream import process_effect_variant_runtime_stream
from minmax.runtime_effect_window import RuntimeEffectActiveWindow
from minmax.runtime_event import RuntimeEvent
from minmax.support_stacking import StackingBehavior


def _effect(**overrides):
    values = {
        "name": "test_effect",
        "layer": EffectLayer.PROC,
        "source": "Test Effect",
        "trigger": "damage_dealt",
        "duration": 5.0,
        "stacking": StackingBehavior.UNIQUE,
    }
    values.update(overrides)
    return EffectVariant(**values)


def _attempt(time_seconds, *, sequence=0, chance_roll=None, target=None, trigger="damage_dealt"):
    return RuntimeEffectEventAttempt(
        event=RuntimeEvent(
            time_seconds=float(time_seconds),
            trigger=trigger,
            source="Observed Event",
            target=target,
            sequence=sequence,
        ),
        chance_roll=chance_roll,
    )


def test_stream_orders_attempts_and_carries_complete_state_forward():
    result = process_effect_variant_runtime_stream(
        (_attempt(4.0), _attempt(1.0)),
        _effect(),
    )

    assert [step.attempt.event.time_seconds for step in result.steps] == [1.0, 4.0]
    assert result.activation_count == 2
    assert result.final_state.activation_state.last_activation_time_seconds == 4.0
    assert len(result.final_state.windows) == 2
    assert result.final_state.windows[0].start_time_seconds == 1.0
    assert result.final_state.windows[0].end_time_seconds == 4.0
    assert result.final_state.windows[1].start_time_seconds == 4.0
    assert result.final_state.windows[1].end_time_seconds == 9.0


def test_stream_cooldown_blocks_middle_attempt_and_allows_later_attempt():
    result = process_effect_variant_runtime_stream(
        (_attempt(1.0), _attempt(5.0), _attempt(11.0)),
        _effect(cooldown=10.0),
    )

    assert [step.activated for step in result.steps] == [True, False, True]
    assert result.steps[1].transition.activation.eligibility.reasons == ("cooldown_active",)
    assert result.final_state.activation_state.last_activation_time_seconds == 11.0
    assert result.activation_count == 2


def test_stream_keeps_chance_roll_attached_to_attempt_when_sorting():
    effect = _effect(chance=0.5, duration=None, stacking=None)
    result = process_effect_variant_runtime_stream(
        (
            _attempt(2.0, chance_roll=0.9),
            _attempt(1.0, chance_roll=0.1),
        ),
        effect,
    )

    assert [step.attempt.chance_roll for step in result.steps] == [0.1, 0.9]
    assert [step.activated for step in result.steps] == [True, False]
    assert result.final_state.activation_state.last_activation_time_seconds == 1.0


def test_stream_preserves_initial_complete_runtime_state():
    existing = RuntimeEffectActiveWindow(
        effect_name="test_effect",
        source="Test Effect",
        start_time_seconds=1.0,
        end_time_seconds=6.0,
    )
    initial = RuntimeEffectRuntimeState(
        activation_state=RuntimeEffectState(last_activation_time_seconds=1.0),
        windows=(existing,),
    )

    result = process_effect_variant_runtime_stream(
        (_attempt(4.0),),
        _effect(cooldown=10.0),
        initial_state=initial,
    )

    assert not result.steps[0].activated
    assert result.final_state == initial


def test_stream_target_cooldowns_advance_independently():
    result = process_effect_variant_runtime_stream(
        (
            _attempt(1.0, target="ally-a"),
            _attempt(2.0, target="ally-b"),
            _attempt(5.0, target="ally-a"),
        ),
        _effect(cooldown=10.0, duration=None, stacking=None),
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )

    assert [step.activated for step in result.steps] == [True, True, False]
    assert result.final_state.activation_state.target_last_activation_times == (
        ("ally-a", 1.0),
        ("ally-b", 2.0),
    )


def test_stream_stacks_overlapping_windows_when_effect_stacks():
    result = process_effect_variant_runtime_stream(
        (_attempt(1.0), _attempt(2.0)),
        _effect(stacking=StackingBehavior.STACKS),
    )

    assert result.activation_count == 2
    assert len(result.final_state.windows) == 2
    assert [window.start_time_seconds for window in result.final_state.windows] == [1.0, 2.0]


def test_unresolved_stacking_is_audited_without_discarding_later_events():
    effect = _effect(stacking=None, cooldown=10.0)
    result = process_effect_variant_runtime_stream(
        (_attempt(1.0), _attempt(2.0)),
        effect,
    )

    assert result.steps[0].activated
    assert not result.steps[0].resolved
    assert result.steps[0].transition.unresolved == ("stacking_behavior_required",)
    assert not result.steps[1].activated
    assert result.steps[1].transition.activation.eligibility.reasons == ("cooldown_active",)
    assert result.final_state.activation_state.last_activation_time_seconds == 1.0
    assert result.final_state.windows == ()
    assert result.unresolved_steps == (result.steps[0],)
    assert not result.resolved


def test_stream_trigger_mismatch_does_not_change_complete_state():
    result = process_effect_variant_runtime_stream(
        (_attempt(1.0, trigger="light_attack"),),
        _effect(),
    )

    assert not result.steps[0].activated
    assert result.steps[0].transition.activation.eligibility.reasons == ("trigger_mismatch",)
    assert result.final_state == RuntimeEffectRuntimeState()


def test_empty_stream_returns_initial_state_and_zero_activations():
    initial = RuntimeEffectRuntimeState(
        activation_state=RuntimeEffectState(last_activation_time_seconds=3.0),
    )
    result = process_effect_variant_runtime_stream((), _effect(), initial_state=initial)

    assert result.steps == ()
    assert result.activation_count == 0
    assert result.final_state == initial
    assert result.resolved
