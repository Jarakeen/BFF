from dataclasses import replace

from minmax.character_progression import CharacterProgression
from services.extreme_hypothetical_resource_active_bar_passive_progression_service import (
    ExtremeHypotheticalResourceActiveBarPassiveProgressionService,
)


class _BaseProgression:
    def normalize(self, progression, route):
        return replace(
            progression,
            owned_skill_lines=("Undaunted",),
            passive_ranks={"Undaunted Mettle": 2},
        )


class _SkillRepository:
    def passive_max_rank(self, name):
        assert name == "Magicka Controller"
        return 2


def _service(objective):
    return ExtremeHypotheticalResourceActiveBarPassiveProgressionService(
        objective_key=objective,
        progression_service=_BaseProgression(),
        skill_line_repository=_SkillRepository(),
    )


def test_max_magicka_adds_canonical_magicka_controller_progression():
    result = _service("max_magicka").normalize(CharacterProgression(passive_ranks={}), object())

    assert result.owns_skill_line("Mages Guild") is True
    assert result.passive_rank("Magicka Controller") == 2
    assert result.passive_rank("Undaunted Mettle") == 2


def test_other_resource_objectives_do_not_buy_magicka_controller():
    for objective in ("max_health", "max_stamina"):
        result = _service(objective).normalize(CharacterProgression(passive_ranks={}), object())
        assert result.owns_skill_line("Mages Guild") is False
        assert result.passive_rank("Magicka Controller") is None
        assert result.passive_rank("Undaunted Mettle") == 2


def test_unreviewed_objective_fails_closed():
    try:
        _service("spell_damage")
    except KeyError as exc:
        assert "active-bar passive objective" in str(exc)
    else:
        raise AssertionError("expected unsupported active-bar passive objective to fail closed")
