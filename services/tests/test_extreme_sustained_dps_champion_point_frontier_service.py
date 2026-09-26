from __future__ import annotations

from dataclasses import dataclass
from math import comb

import pytest

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_champion_point_frontier_service import (
    ExtremeSustainedDPSChampionPointFrontierService,
)


@dataclass(frozen=True)
class _Record:
    name: str
    discipline_index: int | None
    max_points: int = 50


class _Repository:
    def __init__(self):
        self.rows = (
            *(_Record(name, 0) for name in ("A", "B", "C", "D", "E")),
            *(_Record(name, 1) for name in ("F", "G", "H")),
        )

    def slottable_records(self):
        return self.rows

    def get(self, name):
        return next((row for row in self.rows if row.name == name), None)


def _service():
    return ExtremeSustainedDPSChampionPointFrontierService(_Repository())


def test_cp_frontier_counts_four_per_discipline_legality_lazily() -> None:
    result = _service().frontier()

    assert result.denominator_proven is True
    assert result.candidate_count == comb(5, 4)
    assert tuple(axis.selected_count for axis in result.disciplines) == (4, 3)
    assert tuple(axis.combination_count for axis in result.disciplines) == (5, 1)


def test_cp_candidate_indexing_is_deterministic() -> None:
    first = _service().candidate_at(PlayerBuild(), 0)
    last = _service().candidate_at(PlayerBuild(), 4)

    assert first.selected_star_names == ("A", "B", "C", "D", "F", "G", "H")
    assert last.selected_star_names == ("B", "C", "D", "E", "F", "G", "H")
    assert all(entry.Points == "50" for entry in first.build.ChampionPoints)


def test_cp_page_is_lazy() -> None:
    rows = _service().page(PlayerBuild(), offset=1, limit=2)
    assert tuple(row.structural_index for row in rows) == (1, 2)


def test_cp_invalid_index_fails_closed() -> None:
    with pytest.raises(IndexError):
        _service().candidate_at(PlayerBuild(), 5)


def test_cp_duplicate_identity_withholds_denominator() -> None:
    repo = _Repository()
    repo.rows = (*repo.rows, _Record("A", 0))
    result = ExtremeSustainedDPSChampionPointFrontierService(repo).frontier()

    assert result.denominator_proven is False
    assert any("Duplicate" in row for row in result.unresolved)


def test_cp_rejects_boolean_candidate_index() -> None:
    with pytest.raises(TypeError, match="candidate index must be an integer"):
        _service().candidate_at(PlayerBuild(), True)
