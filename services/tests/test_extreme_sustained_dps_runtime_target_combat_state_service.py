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
