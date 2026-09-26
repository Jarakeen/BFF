from __future__ import annotations

from dataclasses import dataclass

import pytest

from minmax.character_progression import CharacterProgression
from services.extreme_skill_universe_service import ExtremeSkillDomain
from services.extreme_sustained_dps_passive_rank_frontier_service import (
    ExtremeSustainedDPSPassiveRankFrontierService,
)


@dataclass(frozen=True)
class _Passive:
    name: str
    skill_line: str
    max_rank: int | None
    domain: ExtremeSkillDomain = ExtremeSkillDomain.GUILD
    combat_line: bool = True


class _Universe:
    def passives(self):
        return (
            _Passive("Class Passive", "Animal Companions", 2, ExtremeSkillDomain.CLASS),
            _Passive("Guild Passive", "Fighters Guild", 2),
            _Passive("Unowned Passive", "Mages Guild", 2),
            _Passive("Race Passive", "High Elf Skills", 3, ExtremeSkillDomain.RACIAL),
        )


def _service():
    return ExtremeSustainedDPSPassiveRankFrontierService(_Universe())


def test_passive_frontier_includes_native_class_and_explicit_owned_lines_only() -> None:
    progression = CharacterProgression(
        owned_skill_lines=("Fighters Guild",),
        passive_ranks={},
    )
    result = _service().frontier(progression, character_class="Warden")

    assert result.denominator_proven is True
    assert tuple(axis.passive_name for axis in result.axes) == (
        "Class Passive",
        "Guild Passive",
    )
    assert result.candidate_count == 3 * 3


def test_passive_candidate_indexes_rank_product_and_preserves_ownership() -> None:
    progression = CharacterProgression(
        owned_skill_lines=("Fighters Guild",),
        passive_ranks={"Existing": 1},
    )
    candidate = _service().candidate_at(
        progression,
        character_class="warden",
        index=8,
    )

    assert candidate.selected_ranks == (
        ("Class Passive", 2),
        ("Guild Passive", 2),
    )
    assert candidate.progression.passive_rank("Existing") == 1
    assert candidate.progression.passive_rank("Class Passive") == 2
    assert candidate.progression.passive_rank("Guild Passive") == 2


def test_passive_frontier_does_not_grant_unowned_shared_or_racial_lines() -> None:
    result = _service().frontier(
        CharacterProgression(owned_skill_lines=(), passive_ranks={}),
        character_class="Warden",
    )

    assert tuple(axis.passive_name for axis in result.axes) == ("Class Passive",)


def test_unknown_class_fails_closed() -> None:
    result = _service().frontier(
        CharacterProgression(owned_skill_lines=("Fighters Guild",), passive_ranks={}),
        character_class="Not A Class",
    )

    assert result.denominator_proven is False
    assert any("Unsupported candidate class" in row for row in result.unresolved)


def test_passive_invalid_index_fails_closed() -> None:
    progression = CharacterProgression(
        owned_skill_lines=("Fighters Guild",),
        passive_ranks={},
    )
    with pytest.raises(IndexError):
        _service().candidate_at(
            progression,
            character_class="Warden",
            index=9,
        )


def test_passive_rejects_boolean_candidate_index() -> None:
    progression = CharacterProgression(
        owned_skill_lines=("Fighters Guild",),
        passive_ranks={},
    )

    with pytest.raises(TypeError, match="candidate index must be an integer"):
        _service().candidate_at(
            progression,
            character_class="Warden",
            index=True,
        )
