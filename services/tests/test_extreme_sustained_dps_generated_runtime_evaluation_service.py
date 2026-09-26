from __future__ import annotations

import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.combat_state import CombatState
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.extreme_dual_bar_set_activation_evidence_service import (
    ExtremeDualBarSetActivationEvidence,
    ExtremeDualBarSetActivationEvidenceCatalog,
    ExtremeDualBarSetActivationScope,
)
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateResult,
)
from services.extreme_sustained_dps_generated_runtime_evaluation_service import (
    ExtremeSustainedDPSExplicitProgressionAdapter,
    _GearBoundRuntimeSnapshotState,
)


def _activation():
    return ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(
            ExtremeDualBarSetActivationEvidence(
                set_id=1,
                set_name="Runtime Set",
                category="test",
                front_count=5,
                back_count=5,
                front_active_breakpoints=(2, 3, 4, 5),
                back_active_breakpoints=(2, 3, 4, 5),
                activation_scope=ExtremeDualBarSetActivationScope.BOTH,
                weapon_only_two_piece=False,
            ),
        )
    )


class _Delegate:
    def __init__(self, effects=(), unresolved=()):
        self.effects = tuple(effects)
        self.unresolved = tuple(unresolved)
        self.received_activation = None

    def resolve(self, build, **kwargs):
        self.received_activation = kwargs.get("gear_activation")
        return ExtremeRuntimeSnapshotCombatStateResult(
            combat_state=CombatState(active_buffs=("Major Courage",)),
            active_effects=self.effects,
            unresolved=self.unresolved,
        )


def _effect(name, *, source="Runtime Set (5)"):
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source=source,
        magnitude=100.0,
        duration=5.0,
        trigger="test_trigger",
        target_type=SupportTargetType.SELF,
    )


def test_explicit_progression_adapter_uses_candidate_attribute_allocation() -> None:
    progression = CharacterProgression(
        attributes=AttributeAllocation(health=64, magicka=0, stamina=0),
        passive_ranks={"Test": 2},
        passive_cp_points={},
    )
    build = PlayerBuild(AttributeHealth=0, AttributeMagicka=64, AttributeStamina=0)

    resolved = ExtremeSustainedDPSExplicitProgressionAdapter(progression).resolve(build)

    assert resolved.resolved is True
    assert resolved.progression.attributes == AttributeAllocation(
        health=0,
        magicka=64,
        stamina=0,
    )
    assert resolved.progression.passive_rank("Test") == 2


def test_gear_bound_projector_injects_activation_and_allows_named_buff_effect() -> None:
    delegate = _Delegate((_effect("major_courage"),))
    service = _GearBoundRuntimeSnapshotState(
        delegate=delegate,
        activation=_activation(),
    )

    result = service.resolve(
        PlayerBuild(),
        progression=CharacterProgression(),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(),
    )

    assert delegate.received_activation == _activation()
    assert result.unresolved == ()


def test_active_non_named_gear_effect_survives_runtime_snapshot_for_context_projection() -> None:
    service = _GearBoundRuntimeSnapshotState(
        delegate=_Delegate((_effect("weapon_spell_damage"),)),
        activation=_activation(),
    )

    result = service.resolve(
        PlayerBuild(),
        progression=CharacterProgression(),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(),
    )

    assert result.unresolved == ()
    assert tuple(effect.name for effect in result.active_effects) == ("weapon_spell_damage",)


def test_non_gear_active_effect_does_not_create_gear_bridge_blocker() -> None:
    service = _GearBoundRuntimeSnapshotState(
        delegate=_Delegate((_effect("weapon_spell_damage", source="Skill Proc"),)),
        activation=_activation(),
    )

    result = service.resolve(
        PlayerBuild(),
        progression=CharacterProgression(),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(),
    )

    assert result.unresolved == ()


@pytest.mark.parametrize(
    "field,value,match",
    (
        ("target_health", True, "target_health must be an integer"),
        ("target_resistance", "18200", "target_resistance must be numeric"),
        ("target_name", 7, "target_name must be a string"),
        ("initial_bar", 1, "initial_bar must be a string"),
    ),
)
def test_generated_runtime_input_boundary_rejects_coerced_scalars(field, value, match) -> None:
    kwargs = {
        "runtime_effects": (),
        "target_health": 1_000_000,
        "target_resistance": 18_200.0,
        "target_name": "Boss",
        "initial_bar": "front",
    }
    kwargs[field] = value

    with pytest.raises(TypeError, match=match):
        from services.extreme_sustained_dps_generated_runtime_evaluation_service import (
            ExtremeSustainedDPSGeneratedRuntimeEvaluationService,
        )
        ExtremeSustainedDPSGeneratedRuntimeEvaluationService._validate_evaluation_inputs(
            **kwargs
        )


def test_generated_runtime_input_boundary_requires_tuple_effects() -> None:
    from services.extreme_sustained_dps_generated_runtime_evaluation_service import (
        ExtremeSustainedDPSGeneratedRuntimeEvaluationService,
    )

    with pytest.raises(TypeError, match="runtime_effects must be a tuple"):
        ExtremeSustainedDPSGeneratedRuntimeEvaluationService._validate_evaluation_inputs(
            runtime_effects=[],  # type: ignore[arg-type]
            target_health=1_000_000,
            target_resistance=18_200.0,
            target_name="Boss",
            initial_bar="front",
        )


def test_generated_runtime_input_boundary_rejects_invalid_ranges() -> None:
    from services.extreme_sustained_dps_generated_runtime_evaluation_service import (
        ExtremeSustainedDPSGeneratedRuntimeEvaluationService,
    )

    with pytest.raises(ValueError, match="target_health must be positive"):
        ExtremeSustainedDPSGeneratedRuntimeEvaluationService._validate_evaluation_inputs(
            runtime_effects=(),
            target_health=0,
            target_resistance=18_200.0,
            target_name="Boss",
            initial_bar="front",
        )

    with pytest.raises(ValueError, match="target_resistance must be finite and non-negative"):
        ExtremeSustainedDPSGeneratedRuntimeEvaluationService._validate_evaluation_inputs(
            runtime_effects=(),
            target_health=1_000_000,
            target_resistance=float("inf"),
            target_name="Boss",
            initial_bar="front",
        )

    with pytest.raises(ValueError, match="initial_bar must be front or back"):
        ExtremeSustainedDPSGeneratedRuntimeEvaluationService._validate_evaluation_inputs(
            runtime_effects=(),
            target_health=1_000_000,
            target_resistance=18_200.0,
            target_name="Boss",
            initial_bar="middle",
        )
