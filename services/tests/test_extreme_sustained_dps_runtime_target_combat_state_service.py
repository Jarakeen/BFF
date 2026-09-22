from __future__ import annotations

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_sustained_dps_runtime_target_combat_state_service import (
    ExtremeSustainedDPSRuntimeTargetCombatStateService,
)


def _attempt(time_seconds: float, *, target: str) -> RuntimeEffectEventAttempt:
    return RuntimeEffectEventAttempt(
        RuntimeEvent(
            time_seconds=time_seconds,
            trigger="damage_dealt",
            source="Attack",
            target=target,
        )
    )


def _vulnerability() -> EffectVariant:
    return EffectVariant(
        name="major_vulnerability",
        layer=EffectLayer.PROC,
        source="Test Vulnerability",
        trigger="damage_dealt",
        duration=4.0,
        target_type=SupportTargetType.ENEMY,
        stacking=StackingBehavior.UNIQUE,
    )


def test_projects_active_enemy_vulnerability_to_matching_target() -> None:
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, target="Boss"),),
        snapshot_time_seconds=2.0,
        runtime_history_complete=True,
    )

    result = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=snapshot,
        effects=(_vulnerability(),),
        target_identity="Boss",
    )

    assert result.unresolved == ()
    assert result.combat_state.active_buffs == ("Major Vulnerability",)


def test_does_not_leak_enemy_effect_to_other_target() -> None:
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, target="Add"),),
        snapshot_time_seconds=2.0,
        runtime_history_complete=True,
    )

    result = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=snapshot,
        effects=(_vulnerability(),),
        target_identity="Boss",
    )

    assert result.unresolved == ()
    assert result.combat_state.active_buffs == ()


def test_exact_expiration_boundary_is_not_active() -> None:
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, target="Boss"),),
        snapshot_time_seconds=5.0,
        runtime_history_complete=True,
    )

    result = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=snapshot,
        effects=(_vulnerability(),),
        target_identity="Boss",
    )

    assert result.combat_state.active_buffs == ()


def _breach() -> EffectVariant:
    return EffectVariant(
        name="major_breach",
        layer=EffectLayer.PROC,
        source="Test Breach",
        trigger="damage_dealt",
        duration=4.0,
        target_type=SupportTargetType.ENEMY,
        stacking=StackingBehavior.UNIQUE,
    )


def test_projects_active_enemy_breach_to_matching_target_state() -> None:
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, target="Boss"),),
        snapshot_time_seconds=2.0,
        runtime_history_complete=True,
    )

    result = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=snapshot,
        effects=(_breach(),),
        target_identity="Boss",
    )

    assert result.unresolved == ()
    assert result.combat_state.active_buffs == ("Major Breach",)


def _brittle() -> EffectVariant:
    return EffectVariant(
        name="minor_brittle",
        layer=EffectLayer.PROC,
        source="Test Brittle",
        trigger="damage_dealt",
        duration=4.0,
        target_type=SupportTargetType.ENEMY,
        stacking=StackingBehavior.UNIQUE,
    )


def test_projects_active_enemy_brittle_to_matching_target_state() -> None:
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, target="Boss"),),
        snapshot_time_seconds=2.0,
        runtime_history_complete=True,
    )

    result = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=snapshot,
        effects=(_brittle(),),
        target_identity="Boss",
    )

    assert result.unresolved == ()
    assert result.combat_state.active_buffs == ("Minor Brittle",)


def test_projects_explicit_numeric_resistance_reduction_to_matching_target() -> None:
    effect = EffectVariant(
        name="synthetic_resistance_debuff",
        layer=EffectLayer.PROC,
        source="Synthetic Debuff",
        trigger="damage_dealt",
        duration=4.0,
        target_type=SupportTargetType.ENEMY,
        resistance_reduction=1234.0,
        stacking=StackingBehavior.UNIQUE,
    )
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, target="Boss"),),
        snapshot_time_seconds=2.0,
        runtime_history_complete=True,
    )

    result = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=snapshot,
        effects=(effect,),
        target_identity="Boss",
    )

    assert result.unresolved == ()
    assert result.combat_state.active_buffs == ()
    assert result.explicit_resistance_reduction == 1234.0


def test_explicit_numeric_resistance_reduction_does_not_leak_targets() -> None:
    effect = EffectVariant(
        name="synthetic_resistance_debuff",
        layer=EffectLayer.PROC,
        source="Synthetic Debuff",
        trigger="damage_dealt",
        duration=4.0,
        target_type=SupportTargetType.ENEMY,
        resistance_reduction=1234.0,
        stacking=StackingBehavior.UNIQUE,
    )
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, target="Add"),),
        snapshot_time_seconds=2.0,
        runtime_history_complete=True,
    )

    result = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=snapshot,
        effects=(effect,),
        target_identity="Boss",
    )

    assert result.explicit_resistance_reduction == 0.0


def test_projects_explicit_numeric_damage_amplification_to_matching_target() -> None:
    effect = EffectVariant(
        name="synthetic_damage_amplification",
        layer=EffectLayer.PROC,
        source="Synthetic Amplifier",
        trigger="damage_dealt",
        duration=4.0,
        target_type=SupportTargetType.ENEMY,
        damage_amplification=0.07,
        stacking=StackingBehavior.UNIQUE,
    )
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, target="Boss"),),
        snapshot_time_seconds=2.0,
        runtime_history_complete=True,
    )

    result = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=snapshot,
        effects=(effect,),
        target_identity="Boss",
    )

    assert result.unresolved == ()
    assert result.combat_state.explicit_damage_taken == 0.07


def test_explicit_numeric_damage_amplification_does_not_leak_targets() -> None:
    effect = EffectVariant(
        name="synthetic_damage_amplification",
        layer=EffectLayer.PROC,
        source="Synthetic Amplifier",
        trigger="damage_dealt",
        duration=4.0,
        target_type=SupportTargetType.ENEMY,
        damage_amplification=0.07,
        stacking=StackingBehavior.UNIQUE,
    )
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, target="Add"),),
        snapshot_time_seconds=2.0,
        runtime_history_complete=True,
    )

    result = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=snapshot,
        effects=(effect,),
        target_identity="Boss",
    )

    assert result.combat_state.explicit_damage_taken == 0.0


def test_named_vulnerability_with_matching_explicit_metadata_is_not_double_counted() -> None:
    effect = EffectVariant(
        name="major_vulnerability",
        layer=EffectLayer.PROC,
        source="Explicit Major Vulnerability",
        trigger="damage_dealt",
        duration=4.0,
        target_type=SupportTargetType.ENEMY,
        damage_amplification=0.10,
        stacking=StackingBehavior.UNIQUE,
    )
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, target="Boss"),),
        snapshot_time_seconds=2.0,
        runtime_history_complete=True,
    )

    result = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=snapshot,
        effects=(effect,),
        target_identity="Boss",
    )

    assert result.combat_state.active_buffs == ("Major Vulnerability",)
    assert result.combat_state.explicit_damage_taken == 0.0
