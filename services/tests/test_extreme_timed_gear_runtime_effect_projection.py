from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.effect_source_persistence import EffectSourcePersistence
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType
from services.extreme_dual_bar_gear_runtime_legality_service import (
    ExtremeDualBarGearRuntimeLegalityService,
)
from services.extreme_dual_bar_set_activation_evidence_service import (
    ExtremeDualBarSetActivationEvidence,
    ExtremeDualBarSetActivationEvidenceCatalog,
    ExtremeDualBarSetActivationScope,
)
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt


class _Resolver:
    def resolve(self, set_id: int, equipped_piece_count: int):
        assert set_id == 77
        assert equipped_piece_count == 5
        return [
            EffectVariant(
                name="weapon_spell_damage",
                layer=EffectLayer.PROC,
                source="Armor of Truth (5)",
                magnitude=460.0,
                duration=10.0,
                trigger="damage_off_balance_target",
                target_type=SupportTargetType.SELF,
                stacking=StackingBehavior.UNIQUE,
                exclusivity_group="armor_of_truth_power",
                source_persistence=EffectSourcePersistence.PERSISTS_AFTER_ACTIVATION,
            )
        ]


def _activation() -> ExtremeDualBarSetActivationEvidenceCatalog:
    return ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(
            ExtremeDualBarSetActivationEvidence(
                set_id=77,
                set_name="Armor of Truth",
                category="Dungeon",
                front_count=5,
                back_count=5,
                front_active_breakpoints=(2, 3, 4, 5),
                back_active_breakpoints=(2, 3, 4, 5),
                activation_scope=ExtremeDualBarSetActivationScope.BOTH,
                weapon_only_two_piece=False,
            ),
        ),
    )


def _attempt(time_seconds: float = 10.0) -> ExtremeRuntimeBarEffectAttempt:
    return ExtremeRuntimeBarEffectAttempt(
        attempt=RuntimeEffectEventAttempt(
            RuntimeEvent(
                time_seconds=time_seconds,
                trigger="damage_off_balance_target",
                source="reviewed Armor of Truth trigger",
            )
        ),
        active_bar="front",
    )


def test_non_named_timed_gear_proc_is_exposed_as_active_effect() -> None:
    result = ExtremeDualBarGearRuntimeLegalityService(resolver=_Resolver()).resolve_history(
        _activation(),
        attempts=(_attempt(),),
        snapshot_time_seconds=15.0,
        snapshot_active_bar="front",
        bar_transition_history_complete=True,
    )

    assert result.unresolved == ()
    assert result.active_buffs == ()
    assert len(result.active_effects) == 1
    effect = result.active_effects[0]
    assert effect.name == "weapon_spell_damage"
    assert effect.magnitude == 460.0
    assert effect.trigger == "damage_off_balance_target"


def test_non_named_timed_gear_proc_expires_normally() -> None:
    result = ExtremeDualBarGearRuntimeLegalityService(resolver=_Resolver()).resolve_history(
        _activation(),
        attempts=(_attempt(),),
        snapshot_time_seconds=20.001,
        snapshot_active_bar="front",
        bar_transition_history_complete=True,
    )

    assert result.unresolved == ()
    assert result.active_effects == ()
