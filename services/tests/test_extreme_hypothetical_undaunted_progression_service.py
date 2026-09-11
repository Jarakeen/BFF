from dataclasses import replace
from types import SimpleNamespace

import pytest

from minmax.character_progression import AttributeAllocation, CharacterProgression
from services.extreme_hypothetical_undaunted_progression_service import (
    ExtremeHypotheticalUndauntedProgressionService,
)


class _ClassProgressionService:
    def normalize(self, progression, route):
        return replace(
            progression,
            owned_skill_lines=("Ardent Flame",),
            passive_ranks={"A Soul Ablaze": 2, "Undaunted Mettle": 1},
        )


class _SkillLineRepository:
    def __init__(self, rank=2):
        self.rank = rank
        self.calls = []

    def passive_max_rank(self, name):
        self.calls.append(name)
        return self.rank


def _progression():
    return CharacterProgression(
        attributes=AttributeAllocation(health=64),
        owned_skill_lines=("Legacy",),
        passive_ranks={"Legacy Passive": 1},
        passive_cp_points={},
    )


def test_normalize_composes_class_progression_and_installs_canonical_mettle_rank():
    repository = _SkillLineRepository(rank=2)
    service = ExtremeHypotheticalUndauntedProgressionService(
        class_progression_service=_ClassProgressionService(),
        skill_line_repository=repository,
    )

    result = service.normalize(_progression(), SimpleNamespace())

    assert result.owns_skill_line("Ardent Flame")
    assert result.owns_skill_line("Undaunted")
    assert result.passive_rank("A Soul Ablaze") == 2
    assert result.passive_rank("Undaunted Mettle") == 2
    assert repository.calls == ["Undaunted Mettle"]


def test_normalize_replaces_existing_mettle_rank_without_duplicate_identity():
    service = ExtremeHypotheticalUndauntedProgressionService(
        class_progression_service=_ClassProgressionService(),
        skill_line_repository=_SkillLineRepository(rank=2),
    )

    result = service.normalize(_progression(), SimpleNamespace())

    matching = [
        name
        for name in result.passive_ranks
        if name.casefold() == "undaunted mettle"
    ]
    assert matching == ["Undaunted Mettle"]
    assert result.passive_ranks["Undaunted Mettle"] == 2


def test_missing_canonical_max_rank_fails_closed():
    service = ExtremeHypotheticalUndauntedProgressionService(
        class_progression_service=_ClassProgressionService(),
        skill_line_repository=_SkillLineRepository(rank=None),
    )

    with pytest.raises(ValueError, match="Canonical max rank is unavailable"):
        service.normalize(_progression(), SimpleNamespace())


def test_constructor_requires_resolvable_dependencies_without_database_path():
    with pytest.raises(ValueError, match="database_path is required"):
        ExtremeHypotheticalUndauntedProgressionService(
            class_progression_service=_ClassProgressionService(),
        )
