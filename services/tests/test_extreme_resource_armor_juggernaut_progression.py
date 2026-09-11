from dataclasses import replace
from types import SimpleNamespace

import pytest

from minmax.character_progression import CharacterProgression
from services.extreme_hypothetical_resource_armor_passive_progression_service import (
    ExtremeHypotheticalResourceArmorPassiveProgressionService,
)


class _ProgressionService:
    def normalize(self, progression, route):
        ranks = dict(progression.passive_ranks or {})
        ranks["Undaunted Mettle"] = 2
        return replace(
            progression,
            owned_skill_lines=("Undaunted",),
            passive_ranks=ranks,
        )


class _SkillLineRepository:
    def passive_max_rank(self, passive_name):
        if passive_name == "Juggernaut":
            return 2
        return None


def _service(objective_key):
    return ExtremeHypotheticalResourceArmorPassiveProgressionService(
        objective_key=objective_key,
        progression_service=_ProgressionService(),
        skill_line_repository=_SkillLineRepository(),
    )


def test_max_health_installs_canonical_max_rank_juggernaut_without_losing_mettle():
    result = _service("max_health").normalize(
        CharacterProgression(passive_ranks={}),
        SimpleNamespace(),
    )

    assert result.owns_skill_line("Undaunted") is True
    assert result.passive_rank("Undaunted Mettle") == 2
    assert result.owns_skill_line("Heavy Armor") is True
    assert result.passive_rank("Juggernaut") == 2


@pytest.mark.parametrize("objective_key", ["max_magicka", "max_stamina"])
def test_non_health_resource_objectives_do_not_buy_juggernaut(objective_key):
    result = _service(objective_key).normalize(
        CharacterProgression(passive_ranks={}),
        SimpleNamespace(),
    )

    assert result.owns_skill_line("Undaunted") is True
    assert result.passive_rank("Undaunted Mettle") == 2
    assert result.owns_skill_line("Heavy Armor") is False
    assert result.passive_rank("Juggernaut") is None


def test_unknown_resource_objective_fails_closed():
    with pytest.raises(KeyError):
        _service("spell_damage")
