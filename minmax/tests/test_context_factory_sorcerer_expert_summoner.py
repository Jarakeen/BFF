from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


class _SkillLines:
    def __init__(self):
        self.lines = {
            "Power Surge": "Storm Calling",
            "Dark Exchange": "Dark Magic",
            "Twilight Matriarch": "Daedric Summoning",
            "Combat Prayer": "Restoration Staff",
        }

    @staticmethod
    def passive_max_rank(name):
        if str(name) in {"Expert Summoner", "Expert Mage"}:
            return 2
        return None

    def skill_line_for_ability_name(self, name):
        return self.lines.get(str(name))


def _factory():
    return BuildCalculationContextFactory(skill_line_repository=_SkillLines())


def _progression(summoner_rank=2, mage_rank=0):
    return CharacterProgression(
        passive_ranks={
            "Expert Summoner": summoner_rank,
            "Expert Mage": mage_rank,
        },
        passive_cp_points={},
    )


def test_factory_applies_expert_summoner_before_resource_state_is_built():
    context = _factory().build(
        character_id="sorcerer",
        build_id="heal",
        build=PlayerBuild(EsoClass="Sorcerer"),
        progression=_progression(),
    )

    assert context.character_state.max_magicka == 12600
    assert context.character_state.max_stamina == 12600
    magicka_labels = [
        step.label
        for stat, trace in context.character_state.traces.items()
        if stat.value == "max_magicka"
        for step in trace.steps
    ]
    stamina_labels = [
        step.label
        for stat, trace in context.character_state.traces.items()
        if stat.value == "max_stamina"
        for step in trace.steps
    ]
    assert "Sorcerer: Expert Summoner" in magicka_labels
    assert "Sorcerer: Expert Summoner" in stamina_labels
    assert context.unresolved_gear_effects == ()


def test_factory_explicit_route_can_remove_native_daedric_summoning():
    context = _factory().build(
        character_id="sorcerer",
        build_id="no-daedric",
        build=PlayerBuild(
            EsoClass="Sorcerer",
            ClassSkillLines=["Dark Magic", "Storm Calling", "Green Balance"],
        ),
        progression=_progression(),
    )

    assert context.character_state.max_magicka == 12000
    assert context.character_state.max_stamina == 12000
    assert context.unresolved_gear_effects == ()


def test_factory_foreign_class_can_gain_expert_summoner_through_subclass_route():
    context = _factory().build(
        character_id="templar",
        build_id="daedric-subclass",
        build=PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Restoring Light", "Daedric Summoning", "Green Balance"],
        ),
        progression=_progression(),
    )

    assert context.character_state.max_magicka == 12600
    assert context.character_state.max_stamina == 12600
    assert context.unresolved_gear_effects == ()


def test_factory_does_not_apply_partial_expert_summoner_rank():
    context = _factory().build(
        character_id="sorcerer",
        build_id="partial",
        build=PlayerBuild(EsoClass="Sorcerer"),
        progression=_progression(summoner_rank=1),
    )

    assert context.character_state.max_magicka == 12000
    assert context.character_state.max_stamina == 12000
    assert any(
        "Partial passive rank is not yet modeled: Expert Summoner 1/2" in message
        for message in context.unresolved_gear_effects
    )


def test_factory_applies_expert_mage_to_weapon_and_spell_damage_from_active_slots():
    context = _factory().build(
        character_id="sorcerer",
        build_id="expert-mage",
        build=PlayerBuild(
            EsoClass="Sorcerer",
            FrontBarSkills=["Power Surge", "Dark Exchange", "Combat Prayer"],
        ),
        progression=_progression(mage_rank=2),
        active_bar="front",
    )

    assert context.core_state is not None
    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == pytest.approx(1216.0)
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == pytest.approx(1216.0)
    assert context.unresolved_gear_effects == ()


def test_factory_route_can_keep_expert_summoner_while_removing_expert_mage():
    context = _factory().build(
        character_id="sorcerer",
        build_id="no-storm-calling",
        build=PlayerBuild(
            EsoClass="Sorcerer",
            ClassSkillLines=["Dark Magic", "Daedric Summoning", "Green Balance"],
            FrontBarSkills=["Twilight Matriarch", "Dark Exchange", "Power Surge"],
        ),
        progression=_progression(mage_rank=2),
    )

    assert context.character_state.max_magicka == 12600
    assert context.core_state is not None
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == pytest.approx(1000.0)


def test_factory_does_not_apply_partial_expert_mage_rank():
    context = _factory().build(
        character_id="sorcerer",
        build_id="partial-expert-mage",
        build=PlayerBuild(
            EsoClass="Sorcerer",
            FrontBarSkills=["Power Surge"],
        ),
        progression=_progression(mage_rank=1),
    )

    assert context.core_state is not None
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == pytest.approx(1000.0)
    assert any(
        "Partial passive rank is not yet modeled: Expert Mage 1/2" in message
        for message in context.unresolved_gear_effects
    )
