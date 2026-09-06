from __future__ import annotations

import sqlite3

from minmax.secondary_ultimate_activation_repository import (
    SecondaryUltimateActivationRepository,
)


def _database(tmp_path, *, base_cost=0, base_mechanic=8, description=None):
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
                description TEXT
            );
            """
        )
        db.execute("INSERT INTO skill VALUES (920, 85982, 'Eternal Guardian')")
        db.execute(
            "INSERT INTO skill_rank VALUES (6930, 920, 85989, 4, 1, 'Eternal Guardian')"
        )
        db.execute(
            "INSERT INTO skill_coefficient VALUES (6930, 1, '8', 0, 0, 0, 1, NULL)"
        )
        db.execute(
            "INSERT INTO ability VALUES (?, ?, ?, ?, ?)",
            (
                85989,
                "Eternal Guardian",
                base_cost,
                base_mechanic,
                description
                if description is not None
                else (
                    "Rouse a grizzly to fight by your side. Once summoned you can activate "
                    "Guardian's Wrath for |cffffff75|r Ultimate, causing the grizzly to maul an enemy."
                ),
            ),
        )
    return path


def test_resolves_explicit_secondary_activation_cost_from_canonical_description(tmp_path) -> None:
    resolution = SecondaryUltimateActivationRepository(_database(tmp_path)).resolve_name(
        "Eternal Guardian"
    )

    assert resolution.unresolved == ()
    assert resolution.activation is not None
    assert resolution.activation.slotted_ability_id == 85989
    assert resolution.activation.slotted_ability_name == "Eternal Guardian"
    assert resolution.activation.activation_name == "Guardian's Wrath"
    assert resolution.activation.cost == 75.0
    assert resolution.activation.source == "ability.description"


def test_does_not_override_positive_base_cost_ultimate(tmp_path) -> None:
    resolution = SecondaryUltimateActivationRepository(
        _database(tmp_path, base_cost=250)
    ).resolve_name("Eternal Guardian")

    assert resolution.activation is None
    assert any("positive canonical base cost" in item for item in resolution.unresolved)


def test_requires_ultimate_resource_mechanic(tmp_path) -> None:
    resolution = SecondaryUltimateActivationRepository(
        _database(tmp_path, base_mechanic=1)
    ).resolve_name("Eternal Guardian")

    assert resolution.activation is None
    assert any("Ultimate resource mechanic" in item for item in resolution.unresolved)


def test_rejects_description_without_explicit_secondary_activation_contract(tmp_path) -> None:
    resolution = SecondaryUltimateActivationRepository(
        _database(
            tmp_path,
            description="This ability mentions 75 Ultimate somewhere but does not define an activation.",
        )
    ).resolve_name("Eternal Guardian")

    assert resolution.activation is None
    assert any("no explicit secondary Ultimate activation cost" in item for item in resolution.unresolved)
