from __future__ import annotations

import sqlite3

from models.build_model import PlayerBuild
from services.extreme_actual_heal_monster_package_service import (
    ExtremeActualHealMonsterPackageService,
)


def _write_fixture(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_bonus (
                id INTEGER PRIMARY KEY,
                set_id INTEGER NOT NULL,
                piece_count INTEGER NOT NULL,
                description TEXT
            );
            CREATE TABLE gear_set_piece (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER
            );
            CREATE TABLE gear_set_item (
                set_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                PRIMARY KEY(set_id, item_id)
            );

            INSERT INTO gear_set VALUES
                (1, 'Body Healer', 'standard', 5),
                (2, 'Broken Body Healer', 'standard', 5),
                (3, 'Monster Healer', 'monster', 2),
                (4, 'Broken Monster', 'monster', 2);

            INSERT INTO gear_set_bonus VALUES
                (1, 1, 2, 'Adds 129 Weapon and Spell Damage'),
                (2, 1, 5, 'Adds 171 Weapon and Spell Damage'),
                (3, 2, 5, 'Adds 400 Weapon and Spell Damage'),
                (4, 3, 2, 'Adds 300 Weapon and Spell Damage'),
                (5, 4, 2, 'Adds 500 Weapon and Spell Damage');

            -- Five distinct non-head/non-shoulder armor positions.
            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES
                (1, 3, 1, 0),
                (1, 8, 1, 0),
                (1, 9, 1, 0),
                (1, 10, 1, 0),
                (1, 13, 1, 0),
                (2, 3, 1, 0),
                (2, 8, 1, 0),
                (2, 9, 1, 0),
                (2, 10, 1, 0),
                (3, 1, 1, 0),
                (3, 4, 1, 0),
                (4, 1, 1, 0);

            INSERT INTO gear_set_item VALUES
                (1, 1001),
                (2, 2001),
                (3, 3001),
                (3, 3002),
                (4, 4001);
            """
        )
        db.commit()


def test_structural_legality_requires_five_body_positions_and_both_monster_slots(tmp_path):
    database = tmp_path / "eso.db"
    _write_fixture(database)
    service = ExtremeActualHealMonsterPackageService(database)

    assert service._ordinary_body_legal(1, "standard") is True
    assert service._ordinary_body_legal(2, "standard") is False
    assert service._monster_body_legal(3, "monster") is True
    assert service._monster_body_legal(4, "monster") is False


def test_reviewed_package_pool_excludes_structurally_illegal_sets(tmp_path):
    database = tmp_path / "eso.db"
    _write_fixture(database)
    service = ExtremeActualHealMonsterPackageService(database)

    ordinary = service._reviewed_names(monster=False, per_objective=10)
    monsters = service._reviewed_names(monster=True, per_objective=10)

    assert ordinary == ("Body Healer",)
    assert monsters == ("Monster Healer",)


def test_package_materializes_five_plus_two_on_real_body_slots(tmp_path):
    database = tmp_path / "eso.db"
    _write_fixture(database)
    service = ExtremeActualHealMonsterPackageService(database)
    baseline = PlayerBuild(BuildName="Healer")
    for slot in baseline.Armor.values():
        slot["Set"] = "Old Set"

    candidates = service.build_candidates(
        baseline,
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.changes[0].path == "Armor.FivePiecePlusMonster"
    assert all(
        candidate.candidate_build.Armor[slot]["Set"] == "Body Healer"
        for slot in service.FIVE_PIECE_BODY_SLOTS
    )
    assert all(
        candidate.candidate_build.Armor[slot]["Set"] == "Monster Healer"
        for slot in service.MONSTER_BODY_SLOTS
    )
    assert all(slot["Set"] == "Old Set" for slot in baseline.Armor.values())
