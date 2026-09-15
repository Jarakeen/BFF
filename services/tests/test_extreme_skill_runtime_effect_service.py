from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_progression import CharacterProgression
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)
from services.extreme_skill_runtime_effect_service import ExtremeSkillRuntimeEffectService


class _Repository:
    def available_skills(self, eso_class):
        return ((101, "Runtime Skill"),)

    def resolve(self, ability_id):
        assert ability_id == 101
        return (
            EffectVariant(
                name="major_sorcery",
                layer=EffectLayer.CAST,
                source="Runtime Skill named",
                magnitude=0.20,
                duration=10.0,
                trigger="critical_heal",
                target_type=SupportTargetType.SELF,
                stacking=StackingBehavior.UNIQUE,
            ),
            EffectVariant(
                name="weapon_spell_damage",
                layer=EffectLayer.CAST,
                source="Runtime Skill flat power",
                magnitude=222.0,
                duration=10.0,
                trigger="critical_heal",
                target_type=SupportTargetType.SELF,
                stacking=StackingBehavior.UNIQUE,
            ),
        )


def _build() -> PlayerBuild:
    return PlayerBuild(
        BuildName="Runtime Skill Build",
        EsoClass="Templar",
        FrontBarSkills=["Runtime Skill", "", "", "", "", ""],
    )


def _attempt(time_seconds: float = 10.0) -> RuntimeEffectEventAttempt:
    return RuntimeEffectEventAttempt(
        RuntimeEvent(
            time_seconds=time_seconds,
            trigger="critical_heal",
            source="runtime skill test",
        )
    )


def test_skill_runtime_service_separates_named_and_non_named_timed_effects() -> None:
    service = ExtremeSkillRuntimeEffectService("unused.db", repository=_Repository())
    result = service.resolve_history(
        _build(),
        active_bar="front",
        attempts=(_attempt(),),
        snapshot_time_seconds=15.0,
    )

    assert result.unresolved == ()
    assert result.active_buffs == ("Major Sorcery",)
    assert len(result.active_effects) == 1
    effect = result.active_effects[0]
    assert effect.name == "weapon_spell_damage"
    assert effect.magnitude == 222.0


def test_skill_runtime_service_expires_both_effect_lanes() -> None:
    service = ExtremeSkillRuntimeEffectService("unused.db", repository=_Repository())
    result = service.resolve_history(
        _build(),
        active_bar="front",
        attempts=(_attempt(),),
        snapshot_time_seconds=20.001,
    )

    assert result.unresolved == ()
    assert result.active_buffs == ()
    assert result.active_effects == ()


def test_shared_runtime_snapshot_projects_skill_named_and_non_named_effects() -> None:
    skill_runtime = ExtremeSkillRuntimeEffectService("unused.db", repository=_Repository())
    result = ExtremeRuntimeSnapshotCombatStateService(
        skill_runtime_effects=skill_runtime,
    ).resolve(
        _build(),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            attempts=(_attempt(),),
            snapshot_time_seconds=15.0,
        ),
    )

    assert result.unresolved == ()
    assert result.combat_state.active_buffs == ("Major Sorcery",)
    assert len(result.active_effects) == 1
    assert result.active_effects[0].name == "weapon_spell_damage"
    assert result.active_effects[0].magnitude == 222.0
