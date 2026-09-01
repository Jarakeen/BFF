from __future__ import annotations

import sqlite3

from minmax.champion_point_static_repository import ChampionPointStaticRepository


def _repository(tmp_path) -> ChampionPointStaticRepository:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE champion_point (
                name TEXT PRIMARY KEY,
                skill_type INTEGER,
                max_points INTEGER,
                jump_points TEXT,
                description TEXT,
                min_description TEXT,
                max_description TEXT
            )
            """
        )
        rows = (
            (
                "From the Brink",
                1,
                50,
                "0,10,20,30,40,50",
                "",
                "When you heal yourself or an ally under 25% Health, you grant them a damage shield.",
                "When you heal yourself or an ally under 25% Health, you grant them a damage shield.",
            ),
            (
                "Rejuvenator",
                1,
                50,
                "0,10,20,30,40,50",
                "",
                "Grants 41 Weapon and Spell Damage to your healing abilities per stage.",
                "Grants 41 Weapon and Spell Damage to your healing abilities per stage.",
            ),
            (
                "Soothing Tide",
                1,
                50,
                "0,10,20,30,40,50",
                "",
                "Increases your Healing Done by area of effect heals by 2% per stage.",
                "Increases your Healing Done by area of effect heals by 2% per stage.",
            ),
            (
                "Swift Renewal",
                1,
                50,
                "0,10,20,30,40,50",
                "",
                "Increases your Healing Done with healing over time effects by 2% per stage.",
                "Increases your Healing Done with healing over time effects by 2% per stage.",
            ),
            (
                "Backstabber",
                1,
                50,
                "0,10,20,30,40,50",
                "",
                "Increases your Critical Damage done by 2% per stage when you are flanking an enemy.",
                "Increases your Critical Damage done by 2% per stage when you are flanking an enemy.",
            ),
        )
        db.executemany("INSERT INTO champion_point VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    return ChampionPointStaticRepository(path)


def test_externally_modeled_dynamic_cp_is_not_reported_as_unresolved(tmp_path):
    repository = _repository(tmp_path)

    for name in ("From the Brink", "Rejuvenator", "Soothing Tide", "Swift Renewal"):
        effects, unresolved = repository.resolve(name, 50)
        assert effects == []
        assert unresolved == []


def test_unmodeled_dynamic_cp_remains_explicitly_unresolved(tmp_path):
    repository = _repository(tmp_path)

    effects, unresolved = repository.resolve("Backstabber", 50)

    assert effects == []
    assert unresolved == ["Champion Point is dynamic or not yet stat-mapped: Backstabber"]
