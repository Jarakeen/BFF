from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_sustained_dps_runtime_self_combat_state_service import (
    ExtremeSustainedDPSRuntimeSelfCombatStateService,
)


def _effect(name="minor_brutality", duration=5.5):
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source="Test Poison IX",
        duration=duration,
        trigger="weapon_poison_proc",
        target_type=SupportTargetType.SELF,
        stacking_behavior=StackingBehavior.UNIQUE,
    )


def _snapshot(effect, *, at=2.0):
    attempt = RuntimeEffectEventAttempt.for_bound_effect(
        event=RuntimeEvent(
            time_seconds=1.0,
            sequence=0,
            trigger="weapon_poison_proc",
            source="Test Poison IX",
            source_bar="front",
        ),
        effect=effect,
        chance_roll=0.0,
    )
    return ExtremeRuntimeSnapshot(
        attempts=(attempt,),
        snapshot_time_seconds=at,
    )


def test_active_self_named_effect_enters_combat_state() -> None:
    effect = _effect()

    result = ExtremeSustainedDPSRuntimeSelfCombatStateService.resolve(
        snapshot=_snapshot(effect),
        effects=(effect,),
    )

    assert result.unresolved == ()
    assert result.combat_state.active_buffs == ("Minor Brutality",)


def test_expired_self_named_effect_is_not_active() -> None:
    effect = _effect(duration=2.0)

    result = ExtremeSustainedDPSRuntimeSelfCombatStateService.resolve(
        snapshot=_snapshot(effect, at=3.1),
        effects=(effect,),
    )

    assert result.unresolved == ()
    assert result.combat_state.active_buffs == ()


def test_unknown_self_named_effect_fails_closed() -> None:
    effect = _effect(name="mystery_self_buff")

    result = ExtremeSustainedDPSRuntimeSelfCombatStateService.resolve(
        snapshot=_snapshot(effect),
        effects=(effect,),
    )

    assert result.combat_state.active_buffs == ()
    assert any(
        "has no canonical named-effect authority" in row
        for row in result.unresolved
    )


def test_enemy_effect_is_not_misprojected_as_self_buff() -> None:
    effect = EffectVariant(
        name="minor_breach",
        layer=EffectLayer.PROC,
        source="Test Poison IX",
        duration=10.0,
        trigger="weapon_poison_proc",
        target="Boss",
        target_type=SupportTargetType.ENEMY,
    )

    result = ExtremeSustainedDPSRuntimeSelfCombatStateService.resolve(
        snapshot=_snapshot(effect),
        effects=(effect,),
    )

    assert result.unresolved == ()
    assert result.combat_state.active_buffs == ()
