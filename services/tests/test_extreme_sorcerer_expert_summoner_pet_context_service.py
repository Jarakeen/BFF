from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.context_factory import BuildCalculationContextFactory
from models.build_model import PlayerBuild
from services.extreme_sorcerer_expert_summoner_pet_context_service import (
    ExtremeSorcererExpertSummonerPetContextService,
)


class _SkillLines:
    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Expert Summoner" else None

    @staticmethod
    def skill_line_for_ability_name(_name):
        return None


def _factory() -> BuildCalculationContextFactory:
    return BuildCalculationContextFactory(skill_line_repository=_SkillLines())


def _resolve(*, build, progression, permanent_pet_active):
    return ExtremeSorcererExpertSummonerPetContextService().resolve(
        factory=_factory(),
        build=build,
        progression=progression,
        character_id="char-1",
        build_id="build-1",
        active_bar="front",
        combat_state=CombatState(),
        permanent_pet_active=permanent_pet_active,
    )


def test_permanent_pet_adds_five_percent_max_health_before_rounding() -> None:
    result = _resolve(
        build=PlayerBuild(EsoClass="Sorcerer"),
        progression=CharacterProgression(
            passive_ranks={"Expert Summoner": 2, "Expert Mage": 0},
        ),
        permanent_pet_active=True,
    )

    assert result.mechanic_complete
    assert result.max_health_bonus_active
    assert result.context.character_state.max_health == 16800
    health_trace = result.context.character_state.traces[next(
        stat for stat in result.context.character_state.traces
        if str(stat.value) == "max_health"
    )]
    assert any(
        step.label == "Sorcerer: Expert Summoner (permanent pet)"
        and step.operation == "percent"
        and step.value == pytest.approx(0.05)
        for step in health_trace.steps
    )


def test_pet_health_percentage_joins_existing_percentage_bucket_additively() -> None:
    # 32 Health attributes: base/attribute subtotal = 16,000 + (32 * 122) = 19,904.
    # Expert Summoner pet branch adds 5% to that subtotal, not 5% to an already
    # rounded finished value.
    result = _resolve(
        build=PlayerBuild(EsoClass="Sorcerer", AttributeHealth=32),
        progression=CharacterProgression(
            attributes=CharacterProgression().attributes.__class__(health=32),
            passive_ranks={"Expert Summoner": 2, "Expert Mage": 0},
        ),
        permanent_pet_active=True,
    )

    assert result.context.character_state.max_health == 20900


def test_inactive_permanent_pet_does_not_invent_health_bonus() -> None:
    result = _resolve(
        build=PlayerBuild(EsoClass="Sorcerer"),
        progression=CharacterProgression(
            passive_ranks={"Expert Summoner": 2, "Expert Mage": 0},
        ),
        permanent_pet_active=False,
    )

    assert result.mechanic_complete
    assert not result.max_health_bonus_active
    assert result.context.character_state.max_health == 16000


def test_removed_daedric_summoning_line_blocks_pet_branch() -> None:
    result = _resolve(
        build=PlayerBuild(
            EsoClass="Sorcerer",
            ClassSkillLines=["Dark Magic", "Storm Calling", "Green Balance"],
        ),
        progression=CharacterProgression(
            passive_ranks={"Expert Summoner": 2, "Expert Mage": 0},
        ),
        permanent_pet_active=True,
    )

    assert not result.max_health_bonus_active
    assert result.context.character_state.max_health == 16000
    assert result.unresolved == (
        "Expert Summoner permanent-pet scenario requires an equipped Daedric Summoning class line",
    )


def test_foreign_class_can_use_explicit_daedric_summoning_pet_branch() -> None:
    result = _resolve(
        build=PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Restoring Light", "Daedric Summoning", "Green Balance"],
        ),
        progression=CharacterProgression(
            passive_ranks={"Expert Summoner": 2},
        ),
        permanent_pet_active=True,
    )

    assert result.mechanic_complete
    assert result.max_health_bonus_active
    assert result.context.character_state.max_health == 16800


def test_missing_expert_summoner_rank_fails_closed() -> None:
    result = _resolve(
        build=PlayerBuild(EsoClass="Sorcerer"),
        progression=CharacterProgression(passive_ranks={"Expert Mage": 0}),
        permanent_pet_active=True,
    )

    assert not result.max_health_bonus_active
    assert result.context.character_state.max_health == 16000
    assert result.unresolved == (
        "Passive rank is not recorded for character: Expert Summoner",
    )
