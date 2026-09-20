from __future__ import annotations

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from models.combat_simulation import SimulationEventPriority
from services.combat_simulation_skill_effect_service import CombatSimulationSkillEffectService


class _Repository:
    def available_skills(self, _character_class):
        return ((6226, "Combat Prayer"),)

    def resolve(self, ability_id):
        assert ability_id == 6226
        return (
            EffectVariant(
                name="minor_resolve",
                layer=EffectLayer.CAST,
                source="Combat Prayer",
                magnitude=2974.0,
                duration=10.0,
                target_type=SupportTargetType.GROUP,
                category=SupportEffectCategory.BUFF,
                stacking=StackingBehavior.UNIQUE,
                exclusivity_group="minor_resolve",
            ),
        )


def _build() -> PlayerBuild:
    return PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        Role="Healer",
        EsoClass="Warden",
    )


def test_combat_prayer_emits_reviewed_minor_resolve_apply_and_expire() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=12.0,
        actions=(
            RotationAction(
                0.0,
                0,
                RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
        ),
    )

    result = CombatSimulationSkillEffectService(
        repository=_Repository()
    ).project(build=_build(), plan=plan)

    assert result.unresolved == ()
    assert len(result.windows) == 1
    window = result.windows[0]
    assert window.effect_name == "minor_resolve"
    assert window.start_time_seconds == 0.0
    assert window.end_time_seconds == 10.0
    assert window.target == "group"
    assert window.magnitude == 2974.0

    assert [
        (event.time_seconds, event.priority, event.event_type)
        for event in result.events
    ] == [
        (0.0, int(SimulationEventPriority.EFFECT_APPLY), "effect_apply"),
        (10.0, int(SimulationEventPriority.EXPIRATION), "effect_expire"),
    ]
    payload = result.events[0].payload_dict()
    assert payload["effect_name"] == "minor_resolve"
    assert payload["target_scope"] == "group"
    assert payload["magnitude"] == 2974.0
    assert payload["duration_seconds"] == 10.0
    assert payload["category"] == "buff"
    assert payload["stacking"] == "unique"


def test_unique_combat_prayer_recast_refreshes_minor_resolve_window() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(
                0.0,
                0,
                RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
            RotationAction(
                6.0,
                0,
                RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
        ),
    )

    result = CombatSimulationSkillEffectService(
        repository=_Repository()
    ).project(build=_build(), plan=plan)

    assert [(window.start_time_seconds, window.end_time_seconds) for window in result.windows] == [
        (0.0, 6.0),
        (6.0, 16.0),
    ]
    assert [
        (event.time_seconds, event.event_type)
        for event in result.events
    ] == [
        (0.0, "effect_apply"),
        (6.0, "effect_apply"),
        (6.0, "effect_expire"),
        (16.0, "effect_expire"),
    ]


def test_unreviewed_condition_fails_closed_instead_of_applying_effect() -> None:
    class _ConditionalRepository(_Repository):
        def resolve(self, _ability_id):
            return (
                EffectVariant(
                    name="minor_lifesteal",
                    layer=EffectLayer.CAST,
                    source="Overflowing Altar",
                    magnitude=600.0,
                    duration=30.0,
                    condition="damage_affected_enemy",
                    target_type=SupportTargetType.ENEMY,
                    category=SupportEffectCategory.DEBUFF,
                    stacking=StackingBehavior.UNIQUE,
                ),
            )

        def available_skills(self, _character_class):
            return ((1, "Overflowing Altar"),)

    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=5.0,
        actions=(
            RotationAction(
                0.0,
                0,
                RotationActionKind.SKILL,
                name="Overflowing Altar",
                bar="front",
            ),
        ),
    )

    result = CombatSimulationSkillEffectService(
        repository=_ConditionalRepository()
    ).project(build=_build(), plan=plan)

    assert result.events == ()
    assert result.windows == ()
    assert result.unresolved == (
        "Overflowing Altar minor_lifesteal at 0s: condition context required: damage_affected_enemy",
    )
