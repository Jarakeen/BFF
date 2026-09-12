from __future__ import annotations

import sqlite3

import pytest

from minmax.race_repository import RaceRepository
from services.extreme_race_objective_service import ExtremeRaceObjectiveService


def _repository(tmp_path):
    database = tmp_path / "race-test.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE race (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                alliance TEXT,
                association TEXT
            );
            CREATE TABLE race_stat (
                id INTEGER PRIMARY KEY,
                race_id INTEGER NOT NULL,
                stat TEXT NOT NULL,
                value INTEGER NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT INTO race(id, name, alliance, association) VALUES (?, ?, '', '')",
            [
                (1, "Beta Race"),
                (2, "Alpha Race"),
                (3, "Gamma Race"),
            ],
        )
        connection.executemany(
            "INSERT INTO race_stat(id, race_id, stat, value) VALUES (?, ?, ?, ?)",
            [
                (1, 1, "spell_damage", 100),
                (2, 2, "spell_damage", 200),
                (3, 2, "weapon_damage", 150),
                (4, 3, "magicka_recovery", 300),
            ],
        )
    return RaceRepository(database)


def test_race_repository_lists_canonical_races_in_deterministic_name_order(tmp_path):
    repository = _repository(tmp_path)

    assert [race.name for race in repository.list_races()] == [
        "Alpha Race",
        "Beta Race",
        "Gamma Race",
    ]


def test_race_repository_list_cache_is_instance_scoped_snapshot(tmp_path):
    repository = _repository(tmp_path)

    first = [race.name for race in repository.list_races()]

    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            "INSERT INTO race(id, name, alliance, association) VALUES (?, ?, '', '')",
            (4, "Delta Race"),
        )

    assert [race.name for race in repository.list_races()] == first
    assert [race.name for race in RaceRepository(repository.database_path).list_races()] == [
        "Alpha Race",
        "Beta Race",
        "Delta Race",
        "Gamma Race",
    ]


def test_extreme_race_candidates_rank_flat_structured_stat_contributions(tmp_path):
    repository = _repository(tmp_path)

    rows = ExtremeRaceObjectiveService.candidates_for_objective(
        repository,
        "spell_damage",
    )

    assert [(row.race_name, row.projected_delta) for row in rows] == [
        ("Alpha Race", 200.0),
        ("Beta Race", 100.0),
        ("Gamma Race", 0.0),
    ]
    assert rows[0].source_stats[0].stat == "spell_damage"


def test_best_race_uses_same_ranked_candidate_path(tmp_path):
    repository = _repository(tmp_path)

    best = ExtremeRaceObjectiveService.best_for_objective(
        repository,
        "magicka_recovery",
    )

    assert best is not None
    assert best.race_name == "Gamma Race"
    assert best.projected_delta == 300.0


def test_unstructured_objective_stays_zero_with_explicit_partial_boundary(tmp_path):
    repository = _repository(tmp_path)

    rows = ExtremeRaceObjectiveService.candidates_for_objective(
        repository,
        "critical_damage",
    )

    assert rows
    assert all(row.projected_delta == 0.0 for row in rows)
    assert all(row.source_stats == () for row in rows)
    assert all("does not prove complete coverage" in row.boundaries[0] for row in rows)


def test_unknown_extreme_race_objective_is_rejected(tmp_path):
    repository = _repository(tmp_path)
    race = repository.list_races()[0]

    with pytest.raises(KeyError, match="unreviewed Extreme race objective"):
        ExtremeRaceObjectiveService.candidate_for_race(
            repository,
            race,
            "max_health",
        )
