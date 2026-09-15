from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_progression import CharacterProgression
from minmax.effect_source_persistence import EffectSourcePersistence
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_bar_transition import ExtremeRuntimeBarTransition
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)
from services.extreme_skill_runtime_effect_service import ExtremeSkillRuntimeEffectService


class _Repository:
    def __init__(self, persistence: EffectSourcePersistence) -> None:
        self.persistence = persistence

    def available_skills(self, eso_class):
        return ((101, "Persistence Skill"),)

    def resolve(self, ability_id):
        assert ability_id == 101
        return (
            EffectVariant(
                name="weapon_spell_damage",
                layer=EffectLayer.CAST,
                source="Persistence Skill",
                magnitude=222.0,
                duration=10.0,
                trigger="critical_heal",
                target_type=SupportTargetType.SELF,
                stacking=StackingBehavior.UNIQUE,
                source_persistence=self.persistence,
            ),
        )


def _build(*, both_bars: bool = False) -> PlayerBuild:
    return PlayerBuild(
        BuildName="Persistence Build",
        EsoClass="Templar",
        FrontBarSkills=["Persistence Skill", "", "", "", "", ""] if both_bars else ["", "", "", "", "", ""],
        BackBarSkills=["Persistence Skill", "", "", "", "", ""],
    )


def _tagged_attempt() -> ExtremeRuntimeBarEffectAttempt:
    return ExtremeRuntimeBarEffectAttempt(
        attempt=RuntimeEffectEventAttempt(
            RuntimeEvent(
                time_seconds=10.0,
                trigger="critical_heal",
                source="persistence test",
                sequence=0,
            )
        ),
        active_bar="back",
    )


def _transition() -> ExtremeRuntimeBarTransition:
    return ExtremeRuntimeBarTransition(11.0, 0, "back", "front")


def _resolve(
    persistence: EffectSourcePersistence,
    *,
    active_bar: str = "front",
    transitions=(_transition(),),
    history_complete: bool = True,
    both_bars: bool = False,
):
    skill_runtime = ExtremeSkillRuntimeEffectService(
        "unused.db",
        repository=_Repository(persistence),
    )
    history = (_tagged_attempt(), *transitions)
    return ExtremeRuntimeSnapshotCombatStateService(
        skill_runtime_effects=skill_runtime,
    ).resolve(
        _build(both_bars=both_bars),
        progression=CharacterProgression(passive_ranks={}),
        active_bar=active_bar,
        snapshot=ExtremeRuntimeSnapshot(
            runtime_history=history,
            snapshot_time_seconds=15.0,
            bar_transition_history_complete=history_complete,
        ),
    )


def test_persists_after_activation_survives_swap_off_source_bar() -> None:
    result = _resolve(EffectSourcePersistence.PERSISTS_AFTER_ACTIVATION)

    assert result.unresolved == ()
    assert len(result.active_effects) == 1
    assert result.active_effects[0].name == "weapon_spell_damage"


def test_requires_source_active_at_snapshot_disappears_off_bar() -> None:
    result = _resolve(EffectSourcePersistence.REQUIRES_SOURCE_ACTIVE_AT_SNAPSHOT)

    assert result.unresolved == ()
    assert result.active_effects == ()


def test_ends_when_source_inactive_is_killed_by_proven_swap() -> None:
    result = _resolve(EffectSourcePersistence.ENDS_WHEN_SOURCE_INACTIVE)

    assert result.unresolved == ()
    assert result.active_effects == ()


def test_ends_when_source_inactive_requires_complete_transition_history() -> None:
    result = _resolve(
        EffectSourcePersistence.ENDS_WHEN_SOURCE_INACTIVE,
        active_bar="back",
        transitions=(),
        history_complete=False,
    )

    assert result.active_effects == ()
    assert any(
        "complete bar-transition history is required" in message
        for message in result.unresolved
    )


def test_ends_when_source_inactive_survives_when_skill_is_on_both_bars() -> None:
    result = _resolve(
        EffectSourcePersistence.ENDS_WHEN_SOURCE_INACTIVE,
        both_bars=True,
    )

    assert result.unresolved == ()
    assert len(result.active_effects) == 1
