from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState, IncomingAttackState
from minmax.context_factory import BuildCalculationContextFactory
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


class _SkillLines:
    @staticmethod
    def skill_line_for_ability_name(name):
        mapping = {
            "Bitter Harvest": "Bone Tyrant",
            "Bone Totem": "Bone Tyrant",
            "Combat Prayer": "Restoration Staff",
        }
        return mapping.get(str(name))

    @staticmethod
    def passive_max_rank(_name):
        return None


def _factory() -> BuildCalculationContextFactory:
    return BuildCalculationContextFactory(skill_line_repository=_SkillLines())


def _gear_inputs(build: PlayerBuild, progression: CharacterProgression, *, active_bar: str = "front"):
    return _factory()._gear_inputs(
        build,
        progression=progression,
        active_bar=active_bar,
        combat_state=CombatState(),
        incoming_attack=IncomingAttackState(),
    )


def test_bone_tyrant_passives_enter_shared_canonical_inputs() -> None:
    build = PlayerBuild(
        EsoClass="Necromancer",
        FrontBarSkills=["Bitter Harvest", "Bone Totem", "Combat Prayer"],
    )
    progression = CharacterProgression(
        passive_ranks={"Last Gasp": 2, "Health Avarice": 2},
    )

    result = _gear_inputs(build, progression)

    assert result.health.skill_flat == 2412.0
    assert result.health.skill_flat_contributions[-1].label == "Necromancer: Last Gasp"
    assert result.core.healing_taken.additive_after_percent[-1].label == "Necromancer: Health Avarice"
    assert result.core.healing_taken.additive_after_percent[-1].value == pytest.approx(0.06)
    assert result.unresolved == ()

    context = _factory().build(
        character_id="necromancer",
        build_id="bone-tyrant",
        build=build,
        progression=progression,
        active_bar="front",
    )
    assert context.character_state.max_health == 18412
    labels = [
        step.label
        for step in context.character_state.traces[StatId.MAX_HEALTH].steps
    ]
    assert "Necromancer: Last Gasp" in labels
    assert context.core_state.derived[StatId.HEALING_TAKEN].final_value == pytest.approx(0.06)
    assert context.unresolved_gear_effects == ()


def test_health_avarice_is_active_bar_specific_but_last_gasp_is_not() -> None:
    build = PlayerBuild(
        EsoClass="Necromancer",
        FrontBarSkills=["Bitter Harvest", "Bone Totem"],
        BackBarSkills=["Combat Prayer"],
    )
    progression = CharacterProgression(
        passive_ranks={"Last Gasp": 2, "Health Avarice": 2},
    )

    front = _gear_inputs(build, progression, active_bar="front")
    back = _gear_inputs(build, progression, active_bar="back")

    assert front.health.skill_flat == 2412.0
    assert back.health.skill_flat == 2412.0
    assert front.core.healing_taken.additive_after_percent[-1].value == pytest.approx(0.06)
    assert back.core.healing_taken.additive_after_percent == ()


def test_bone_tyrant_route_fails_closed_when_passive_ranks_are_missing() -> None:
    result = _gear_inputs(
        PlayerBuild(EsoClass="Necromancer", FrontBarSkills=["Bone Totem"]),
        CharacterProgression(passive_ranks={}),
    )

    assert result.health.skill_flat == 0.0
    assert result.core.healing_taken.additive_after_percent == ()
    assert "Passive rank is not recorded for character: Last Gasp" in result.unresolved
    assert "Passive rank is not recorded for character: Health Avarice" in result.unresolved


def test_explicit_route_without_bone_tyrant_does_not_request_its_passives() -> None:
    result = _gear_inputs(
        PlayerBuild(
            EsoClass="Necromancer",
            ClassSkillLines=["Grave Lord", "Living Death", "Siphoning"],
            FrontBarSkills=["Bone Totem"],
        ),
        CharacterProgression(passive_ranks={}),
    )

    assert result.health.skill_flat == 0.0
    assert result.core.healing_taken.additive_after_percent == ()
    assert not any("Last Gasp" in message for message in result.unresolved)
    assert not any("Health Avarice" in message for message in result.unresolved)
