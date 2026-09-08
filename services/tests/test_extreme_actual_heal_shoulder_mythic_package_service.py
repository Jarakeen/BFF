from __future__ import annotations

import sqlite3
from pathlib import Path

from models.build_model import PlayerBuild
from services.extreme_actual_heal_shoulder_mythic_package_service import (
    ExtremeActualHealShoulderMythicPackageService,
)


def _write_db(path: Path) -> None:
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
                (1, 'Primary Healer', 'standard', 5),
                (2, 'Secondary Healer', 'standard', 5),
                (3, 'Shoulder Mythic', 'standard', 1),
                (4, 'Ring Mythic', 'standard', 1),
                (5, 'No Ring Secondary', 'standard', 5),
                (6, 'Wrong Staff Secondary', 'standard', 5);

            INSERT INTO gear_set_bonus VALUES
                (1, 1, 5, 'Adds 171 Weapon and Spell Damage'),
                (2, 2, 5, 'Adds 171 Weapon and Spell Damage'),
                (3, 3, 1, 'Adds 171 Weapon and Spell Damage'),
                (4, 4, 1, 'Adds 171 Weapon and Spell Damage'),
                (5, 5, 5, 'Adds 171 Weapon and Spell Damage'),
                (6, 6, 5, 'Adds 171 Weapon and Spell Damage');

            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES
                (1, 2, 1, 0),
                (1, 3, 1, 0),
                (1, 5, 1, 0),
                (1, 6, 1, 0),
                (1, 7, 1, 0),

                (2, 1, 1, 0),
                (2, 8, 0, 0),
                (2, 9, 0, 0),
                (2, 11, 0, 9),

                (3, 4, 1, 0),
                (4, 9, 0, 0),

                (5, 1, 1, 0),
                (5, 8, 0, 0),
                (5, 11, 0, 9),

                (6, 1, 1, 0),
                (6, 8, 0, 0),
                (6, 9, 0, 0),
                (6, 11, 0, 12);

            INSERT INTO gear_set_item VALUES
                (1, 1001),
                (2, 2001),
                (3, 3001),
                (4, 4001),
                (5, 5001),
                (6, 6001);
            """
        )


def test_shoulder_mythic_shape_is_required(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealShoulderMythicPackageService(database)

    assert service._shoulder_mythic_legal(3, "standard") is True
    assert service._shoulder_mythic_legal(4, "standard") is False


def test_secondary_requires_head_neck_ring_and_exact_weapon(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealShoulderMythicPackageService(database)

    assert service._secondary_without_shoulders_legal(
        2, "standard", weapon_type_id=9
    ) is True
    assert service._secondary_without_shoulders_legal(
        5, "standard", weapon_type_id=9
    ) is False
    assert service._secondary_without_shoulders_legal(
        6, "standard", weapon_type_id=9
    ) is False
    assert service._secondary_without_shoulders_legal(
        6, "standard", weapon_type_id=12
    ) is True


def test_builds_real_five_plus_five_plus_one_shoulder_mythic_package(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealShoulderMythicPackageService(database)
    build = PlayerBuild(BuildName="Healer")
    build.FrontBarWeapon.WeaponType = "Restoration Staff"
    build.Ring2.Set = "Old Extra Set"

    candidates = service.build_candidates(
        build,
        character_id="char-1",
        baseline_build_id="build-1",
        active_bar="front",
        primary_per_objective=6,
        secondary_per_objective=6,
        mythic_per_objective=6,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    result = candidate.candidate_build
    assert candidate.changes[0].path == "Gear.FivePiecePlusFivePiecePlusShoulderMythic"
    assert all(
        result.Armor[slot]["Set"] == "Primary Healer"
        for slot in ("Chest", "Legs", "Hands", "Waist", "Feet")
    )
    assert result.Armor["Head"]["Set"] == "Secondary Healer"
    assert result.Armor["Shoulders"]["Set"] == "Shoulder Mythic"
    assert result.Necklace.Set == "Secondary Healer"
    assert result.Ring1.Set == "Secondary Healer"
    assert result.Ring2.Set == ""
    assert result.FrontBarWeapon.Set == "Secondary Healer"
    assert result.FrontBarWeapon.WeaponType == "Restoration Staff"
    assert build.Armor["Shoulders"]["Set"] == ""
    assert build.Ring2.Set == "Old Extra Set"
