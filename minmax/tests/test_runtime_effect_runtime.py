from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_eligibility import RuntimeCooldownScope
from minmax.runtime_effect_runtime import (
    RuntimeEffectRuntimeState,
    apply_effect_variant_runtime_event,
)
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


def _event(**overrides):
    values = {
        "time_seconds": 10.0,
        "trigger": "damage_dealt",
        "source": "Test Event",
        "sequence": 1,
    }
    values.update(overrides)
    return RuntimeEvent(**values)


def test_failed_activation_preserves_combined_runtime_state():
    existing = RuntimeEffectActiveWindow(
        effect_name="test_effect",
        source="Old",
        start_time_seconds=1.0,
        end_time_seconds=3.0,
    )
    state = RuntimeEffectRuntimeState(windows=(existing,))

    result = apply_effect_variant_runtime_event(
        _event(trigger="light_attack"),
        _effect(),
        state=state,
    )

    assert not result.activated
    assert result.state is state
    assert result.stacking is None


def test_successful_bounded_activation_updates_cooldown_and_window_state():
    result = apply_effect_variant_runtime_event(_event(), _effect())

    assert result.activated
    assert result.resolved
    assert result.state.activation_state.last_activation_time_seconds == 10.0
    assert len(result.state.windows) == 1
    assert result.state.windows[0].start_time_seconds == 10.0
    assert result.state.windows[0].end_time_seconds == 15.0


def test_unique_reactivation_refreshes_existing_window():
    first = apply_effect_variant_runtime_event(_event(time_seconds=10.0), _effect())
    second = apply_effect_variant_runtime_event(
        _event(time_seconds=12.0, sequence=2),
        _effect(),
        state=first.state,
    )

    assert second.activated
    assert second.resolved
    assert len(second.state.windows) == 2
    assert second.state.windows[0].start_time_seconds == 10.0
    assert second.state.windows[0].end_time_seconds == 12.0
    assert second.state.windows[1].start_time_seconds == 12.0
    assert second.state.windows[1].end_time_seconds == 17.0


def test_stacks_behavior_retains_overlapping_windows():
    effect = _effect(stacking=StackingBehavior.STACKS)
    first = apply_effect_variant_runtime_event(_event(time_seconds=10.0), effect)
    second = apply_effect_variant_runtime_event(
        _event(time_seconds=12.0, sequence=2),
        effect,
        state=first.state,
    )

    assert second.resolved
    assert len(second.state.windows) == 2
    assert tuple(window.end_time_seconds for window in second.state.windows) == (15.0, 17.0)


def test_missing_stacking_policy_records_activation_but_leaves_windows_unchanged():
    existing = RuntimeEffectActiveWindow(
        effect_name="other_effect",
        source="Other",
        start_time_seconds=1.0,
        end_time_seconds=20.0,
    )
    state = RuntimeEffectRuntimeState(windows=(existing,))

    result = apply_effect_variant_runtime_event(
        _event(),
        _effect(stacking=None),
        state=state,
    )

    assert result.activated
    assert not result.resolved
    assert result.unresolved == ("stacking_behavior_required",)
    assert result.state.activation_state.last_activation_time_seconds == 10.0
    assert result.state.windows == (existing,)


def test_instantaneous_effect_updates_activation_state_without_window_or_stacking_requirement():
    result = apply_effect_variant_runtime_event(
        _event(),
        _effect(duration=0.0, stacking=None),
    )

    assert result.activated
    assert result.resolved
    assert result.state.activation_state.last_activation_time_seconds == 10.0
    assert result.state.windows == ()
    assert result.stacking is None


def test_global_cooldown_blocks_second_event_and_preserves_windows():
    effect = _effect(cooldown=10.0)
    first = apply_effect_variant_runtime_event(_event(time_seconds=10.0), effect)
    second = apply_effect_variant_runtime_event(
        _event(time_seconds=15.0, sequence=2),
        effect,
        state=first.state,
    )

    assert not second.activated
    assert second.activation.eligibility.reasons == ("cooldown_active",)
    assert second.state == first.state


def test_target_scoped_runtime_transition_tracks_target_history_and_windows():
    effect = _effect(cooldown=10.0)
    first = apply_effect_variant_runtime_event(
        _event(time_seconds=10.0, target="ally-a"),
        effect,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )
    second = apply_effect_variant_runtime_event(
        _event(time_seconds=11.0, target="ally-b", sequence=2),
        effect,
        state=first.state,
        cooldown_scope=RuntimeCooldownScope.TARGET,
    )

    assert second.activated
    assert second.state.activation_state.last_activation_for_target("ally-a") == 10.0
    assert second.state.activation_state.last_activation_for_target("ally-b") == 11.0
    assert {window.target for window in second.state.windows} == {"ally-a", "ally-b"}


def test_failed_chance_roll_does_not_change_activation_or_window_state():
    effect = _effect(chance=0.5)
    first = apply_effect_variant_runtime_event(
        _event(time_seconds=10.0),
        effect,
        chance_roll=0.1,
    )
    second = apply_effect_variant_runtime_event(
        _event(time_seconds=12.0, sequence=2),
        effect,
        state=first.state,
        chance_roll=0.9,
    )

    assert not second.activated
    assert second.activation.eligibility.reasons == ("chance_failed",)
    assert second.state == first.state
