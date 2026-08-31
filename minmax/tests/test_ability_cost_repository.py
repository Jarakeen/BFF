from __future__ import annotations

import sqlite3

from minmax.ability_cost_repository import AbilityCostRepository
from minmax.resource_costs import ResourceType


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER NOT NULL,
                name TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                rank INTEGER,
                morph INTEGER,
                raw_name TEXT
            );
            CREATE TABLE skill_coefficient (
                skill_rank_id INTEGER NOT NULL,
                coefficient_number INTEGER NOT NULL,
                type TEXT,
                a REAL,
                b REAL,
                c REAL,
                r REAL,
                avg REAL
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                base_cost REAL,
                base_mechanic INTEGER,
                skill_line TEXT
            );
            """
        )
        db.execute("INSERT INTO skill VALUES (10, 1000, 'Combat Prayer')")
        db.execute("INSERT INTO skill_rank VALUES (20, 10, 41151, 4, 1, 'Combat Prayer')")
        db.execute("INSERT INTO skill_coefficient VALUES (20, 1, '8', .1, 1.0, 0, 1, NULL)")
        db.execute("INSERT INTO ability VALUES (41151, 'Combat Prayer', 4590, 1, 'Restoration Staff')")
    return path


def test_resolve_name_promotes_rank_specific_base_cost(tmp_path) -> None:
    repository = AbilityCostRepository(_database(tmp_path))

    resolved = repository.resolve_name("Combat Prayer")

    assert resolved.unresolved == ()
    assert resolved.name == "Combat Prayer"
    assert resolved.skill_line == "Restoration Staff"
    assert resolved.base_cost is not None
    assert resolved.base_cost.ability_id == 41151
    assert resolved.base_cost.rank == 4
    assert resolved.base_cost.morph == 1
    assert resolved.base_cost.amount == 4590
    assert resolved.base_cost.resources == (ResourceType.MAGICKA,)


def test_resolve_name_rejects_non_cost_skill_explicitly(tmp_path) -> None:
    path = _database(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE ability SET base_cost = 0 WHERE ability_id = 41151")

    resolved = AbilityCostRepository(path).resolve_name("Combat Prayer")

    assert resolved.base_cost is None
    assert any("no positive canonical base cost" in item for item in resolved.unresolved)


def test_resolve_name_preserves_unsupported_resource_mechanic(tmp_path) -> None:
    path = _database(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE ability SET base_mechanic = 64 WHERE ability_id = 41151")

    resolved = AbilityCostRepository(path).resolve_name("Combat Prayer")

    assert resolved.base_cost is None
    assert any("Unsupported resource mechanic bits" in item for item in resolved.unresolved)
