from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState, IncomingAttackState
from minmax.context_factory import BuildCalculationContextFactory
from models.build_model import PlayerBuild


class _SkillLines:
    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Balanced Warrior" else None

    @staticmethod
    def skill_line_for_ability_name(_name):
        return None


def _factory() -> BuildCalculationContextFactory:
    return BuildCalculationContextFactory(skill_line_repository=_SkillLines())


def _gear_inputs(build: PlayerBuild, progression: CharacterProgression):
    return _factory()._gear_inputs(
        build,
        progression=progression,
        active_bar="front",
        combat_state=CombatState(),
        incoming_attack=IncomingAttackState(),
    )


def test_balanced_warrior_enters_canonical_weapon_and_spell_damage_buckets():
    result = _gear_inputs(
        PlayerBuild(EsoClass="Templar"),
        CharacterProgression(passive_ranks={"Balanced Warrior": 2}),
    )

    weapon = result.core.weapon_damage.percent[-1]
    spell = result.core.spell_damage.percent[-1]
    assert weapon.label == "Templar: Balanced Warrior"
    assert spell.label == "Templar: Balanced Warrior"
    assert weapon.value == pytest.approx(0.06)
    assert spell.value == pytest.approx(0.06)
    assert result.applied_effect_count == 2
    assert result.unresolved == ()


def test_explicit_subclass_route_without_aedric_spear_does_not_request_balanced_warrior():
    result = _gear_inputs(
        PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Restoring Light", "Dawn's Wrath", "Green Balance"],
        ),
        CharacterProgression(passive_ranks={}),
    )

    assert not any(
        contribution.label == "Templar: Balanced Warrior"
        for contribution in result.core.spell_damage.percent
    )
    assert not any("Balanced Warrior" in message for message in result.unresolved)


def test_aedric_spear_route_fails_closed_when_balanced_warrior_rank_is_missing():
    result = _gear_inputs(
        PlayerBuild(EsoClass="Templar"),
        CharacterProgression(passive_ranks={}),
    )

    assert not result.core.spell_damage.percent
    assert result.unresolved == (
        "Passive rank is not recorded for character: Balanced Warrior",
    )
