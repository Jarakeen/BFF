from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState, IncomingAttackState
from minmax.context_factory import BuildCalculationContextFactory
from models.build_model import PlayerBuild


class _SkillLines:
    @staticmethod
    def passive_max_rank(name):
        if name in {"Dark Vigor", "Magicka Flood"}:
            return 2
        return None

    @staticmethod
    def skill_line_for_ability_name(name):
        mapping = {
            "Refreshing Path": "Shadow",
            "Dark Cloak": "Shadow",
            "Healthy Offering": "Siphoning",
        }
        return mapping.get(str(name))


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


def test_dark_vigor_enters_canonical_max_health_bucket_from_progression() -> None:
    result = _gear_inputs(
        PlayerBuild(
            EsoClass="Nightblade",
            FrontBarSkills=["Refreshing Path", "Dark Cloak"],
        ),
        CharacterProgression(
            passive_ranks={"Dark Vigor": 2, "Magicka Flood": 0},
        ),
    )

    contribution = result.health.skill_percent_contributions[-1]
    assert contribution.label == "Nightblade: Dark Vigor"
    assert contribution.value == pytest.approx(0.10)
    assert result.applied_effect_count == 1
    assert result.unresolved == ()


def test_explicit_route_without_shadow_does_not_request_dark_vigor() -> None:
    result = _gear_inputs(
        PlayerBuild(
            EsoClass="Nightblade",
            ClassSkillLines=["Assassination", "Siphoning", "Green Balance"],
            FrontBarSkills=["Refreshing Path"],
        ),
        CharacterProgression(passive_ranks={"Magicka Flood": 0}),
    )

    assert result.health.skill_percent_contributions == ()
    assert not any("Dark Vigor" in message for message in result.unresolved)


def test_shadow_route_fails_closed_when_dark_vigor_rank_is_missing() -> None:
    result = _gear_inputs(
        PlayerBuild(
            EsoClass="Nightblade",
            FrontBarSkills=["Refreshing Path"],
        ),
        CharacterProgression(passive_ranks={"Magicka Flood": 0}),
    )

    assert result.health.skill_percent_contributions == ()
    assert "Passive rank is not recorded for character: Dark Vigor" in result.unresolved


def test_foreign_class_shadow_route_can_receive_dark_vigor() -> None:
    result = _gear_inputs(
        PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Shadow"],
            FrontBarSkills=["Refreshing Path"],
        ),
        CharacterProgression(passive_ranks={"Dark Vigor": 2}),
    )

    contribution = result.health.skill_percent_contributions[-1]
    assert contribution.label == "Nightblade: Dark Vigor"
    assert contribution.value == pytest.approx(0.05)
    assert result.unresolved == ()
