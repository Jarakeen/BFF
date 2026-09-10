from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


class _SkillLines:
    @staticmethod
    def passive_max_rank(_name):
        return None

    @staticmethod
    def skill_line_for_ability_name(_name):
        return None


def _context(build: PlayerBuild, progression: CharacterProgression):
    return BuildCalculationContextFactory(skill_line_repository=_SkillLines()).build(
        character_id="dragonknight-test",
        build_id="dragonknight-build",
        build=build,
        progression=progression,
    )


def test_rank_two_soul_ablaze_enters_canonical_healing_taken() -> None:
    context = _context(
        PlayerBuild(EsoClass="Dragonknight"),
        CharacterProgression(passive_ranks={"A Soul Ablaze": 2}),
    )

    trace = context.core_state.derived[StatId.HEALING_TAKEN]
    assert trace.final_value == pytest.approx(0.08)
    assert any(step[0] == "Dragonknight: A Soul Ablaze" for step in trace.steps)
    assert context.unresolved_gear_effects == ()


def test_rank_one_soul_ablaze_preserves_reviewed_four_percent_value() -> None:
    context = _context(
        PlayerBuild(EsoClass="Dragonknight"),
        CharacterProgression(passive_ranks={"A Soul Ablaze": 1}),
    )

    assert context.core_state.derived[StatId.HEALING_TAKEN].final_value == pytest.approx(0.04)
    assert context.unresolved_gear_effects == ()


def test_explicit_route_without_ardent_flame_does_not_request_soul_ablaze() -> None:
    context = _context(
        PlayerBuild(
            EsoClass="Dragonknight",
            ClassSkillLines=["Draconic Power", "Earthen Heart", "Restoring Light"],
        ),
        CharacterProgression(passive_ranks={}),
    )

    assert context.core_state.derived[StatId.HEALING_TAKEN].final_value == pytest.approx(0.0)
    assert not any("A Soul Ablaze" in message for message in context.unresolved_gear_effects)


def test_ardent_flame_route_fails_closed_when_soul_ablaze_rank_is_missing() -> None:
    context = _context(
        PlayerBuild(EsoClass="Dragonknight"),
        CharacterProgression(passive_ranks={}),
    )

    assert context.core_state.derived[StatId.HEALING_TAKEN].final_value == pytest.approx(0.0)
    assert "Passive rank is not recorded for character: A Soul Ablaze" in context.unresolved_gear_effects
