from __future__ import annotations

import sqlite3

from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from services.extreme_resource_champion_point_state_service import (
    ExtremeResourceChampionPointStateService,
)
from services.extreme_resource_runtime_skill_witness_catalog_service import (
    ExtremeResourceRuntimeSkillWitnessCatalogService,
)


def _write_cp_db(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE champion_point (
                id INTEGER PRIMARY KEY,
                name TEXT,
                skill_type INTEGER,
                max_points INTEGER,
                jump_points TEXT,
                min_description TEXT,
                max_description TEXT,
                description TEXT
            );
            INSERT INTO champion_point VALUES (
                1, 'Eldritch Insight', 0, 20, '', NULL, NULL,
                'Grants 26 Max Magicka per stage.'
            );
            INSERT INTO champion_point VALUES (
                2, 'Arcane Supremacy', 2, 50, '', NULL, NULL,
                'Grants 28 Max Magicka per stage.'
            );
            """
        )


def _write_skill_db(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                class_type TEXT,
                skill_line TEXT,
                skill_type TEXT,
                is_passive INTEGER NOT NULL,
                is_player INTEGER NOT NULL,
                is_crafted INTEGER NOT NULL DEFAULT 0,
                base_ability_id INTEGER,
                description TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                rank INTEGER NOT NULL,
                ability_id INTEGER NOT NULL
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                description TEXT
            );

            INSERT INTO skill VALUES (
                1, 'Harness Magicka', '', 'Light Armor', 'Active', 0, 1, 0, 1001,
                'Create a shield around yourself.'
            );
            INSERT INTO skill VALUES (
                2, 'Summon Unstable Familiar', 'Sorcerer', 'Daedric Summoning', 'Active', 0, 1, 0, 1002,
                'Summon a familiar to fight at your side. The familiar remains until killed or unsummoned.'
            );
            INSERT INTO skill VALUES (
                3, 'Werewolf Transformation', '', 'Werewolf', 'Ultimate', 0, 1, 0, 1003,
                'Transform into a beast.'
            );

            INSERT INTO skill_rank VALUES (1, 1, 4, 2001);
            INSERT INTO skill_rank VALUES (2, 2, 4, 2002);
            INSERT INTO skill_rank VALUES (3, 3, 4, 2003);
            INSERT INTO ability VALUES (2001, 'Create a shield around yourself.');
            INSERT INTO ability VALUES (2002, 'Summon a familiar to fight at your side. The familiar remains until killed or unsummoned.');
            INSERT INTO ability VALUES (2003, 'Transform into a beast.');
            """
        )


def test_production_cp_state_is_shared_across_service_instances(tmp_path) -> None:
    path = tmp_path / "cp.db"
    _write_cp_db(path)

    first = ExtremeResourceChampionPointStateService(path).build("max_magicka")
    second = ExtremeResourceChampionPointStateService(path).build("MAX_MAGICKA")

    assert second is first
    assert first.denominator_proven is True
    assert first.non_slottable_allocations == (("Eldritch Insight", 20, 520.0),)
    assert first.slottable_allocations == (("Arcane Supremacy", 50, 1400.0),)


def test_production_runtime_witness_catalog_is_shared_across_service_instances(tmp_path) -> None:
    path = tmp_path / "skills.db"
    _write_skill_db(path)

    first = ExtremeResourceRuntimeSkillWitnessCatalogService(path).build()
    second = ExtremeResourceRuntimeSkillWitnessCatalogService(path).build()

    assert second is first
    assert first.denominator_proven is True
    assert [row.canonical_id for row in first.armor_abilities] == ["harness_magicka"]
    assert [row.canonical_id for row in first.pet_abilities] == ["summon_unstable_familiar"]
    assert [row.canonical_id for row in first.transformation_ultimates] == [
        "werewolf_transformation"
    ]


def test_mundus_repository_reuses_instance_reads_but_fresh_instance_sees_database(tmp_path) -> None:
    path = tmp_path / "mundus.db"
    MundusRepository(path, game_update=U50_GAME_UPDATE, initialize=True)

    class _CountingRepository(MundusRepository):
        def __init__(self, database_path) -> None:
            super().__init__(database_path, game_update=U50_GAME_UPDATE, initialize=False)
            self.connect_calls = 0

        def _connect(self):
            self.connect_calls += 1
            return super()._connect()

    repository = _CountingRepository(path)

    assert "The Mage" in repository.list_names()
    assert "The Mage" in repository.list_names()
    assert repository.connect_calls == 1

    first_records = repository.get_records("The Mage")
    second_records = repository.get_records("The Mage")
    assert second_records == first_records
    assert repository.connect_calls == 2

    first_effects = repository.get_effects("The Mage")
    second_effects = repository.get_effects("The Mage")
    assert second_effects == first_effects
    assert repository.connect_calls == 2

    with sqlite3.connect(path) as db:
        db.execute(
            """
            UPDATE mundus_effect
            SET value = 9999
            WHERE mundus_id = (
                SELECT id FROM mundus_stone
                WHERE name = 'The Mage' AND game_update = ?
            )
            """,
            (U50_GAME_UPDATE,),
        )

    assert repository.get_records("The Mage") == first_records
    fresh = MundusRepository(path, game_update=U50_GAME_UPDATE, initialize=False)
    assert fresh.get_records("The Mage")[0].value == 9999.0
