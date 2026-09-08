from __future__ import annotations

import sqlite3
from pathlib import Path

from models.build_model import PlayerBuild
from services.extreme_actual_heal_mythic_package_service import (
    ExtremeActualHealMythicPackageService,
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
                (3, 'Ring Mythic', 'standard', 1),
                (4, 'Neck Mythic', 'standard', 1),
                (5, 'Wrong Staff Healer', 'standard', 5);

            INSERT INTO gear_set_bonus VALUES
                (1, 1, 5, 'Adds 171 Weapon and Spell Damage'),
                (2, 2, 5, 'Adds 171 Weapon and Spell Damage'),
                (3, 3, 1, 'Adds 171 Weapon and Spell Damage'),
                (4, 4, 1, 'Adds 171 Weapon and Spell Damage'),
                (5, 5, 5, 'Adds 171 Weapon and Spell Damage');

            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES
                (1, 2, 1, 0),
                (1, 3, 1, 0),
                (1, 5, 1, 0),
                (1, 6, 1, 0),
                (1, 7, 1, 0),
                (2, 1, 1, 0),
                (2, 4, 1, 0),
                (2, 8, 0, 0),
                (2, 11, 0, 9),
                (3, 9, 0, 0),
                (4, 8, 0, 0),
                (5, 1, 1, 0),
                (5, 4, 1, 0),
                (5, 8, 0, 0),
                (5, 11, 0, 12);

            INSERT INTO gear_set_item VALUES
                (1, 1001),
                (2, 2001),
                (3, 3001),
                (4, 4001),
                (5, 5001);
            """
        )


def test_ring_mythic_shape_is_required(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealMythicPackageService(database)

    assert service._ring_mythic_legal(3, "standard") is True
    assert service._ring_mythic_legal(4, "standard") is False


def test_secondary_set_requires_exact_active_weapon_subtype(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealMythicPackageService(database)

    assert service._secondary_legal(2, "standard", weapon_type_id=9) is True
    assert service._secondary_legal(2, "standard", weapon_type_id=12) is False
    assert service._secondary_legal(5, "standard", weapon_type_id=12) is True
    assert service._secondary_legal(5, "standard", weapon_type_id=9) is False


def test_builds_real_five_plus_five_plus_one_ring_mythic_package(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealMythicPackageService(database)
    build = PlayerBuild(BuildName="Healer")
    build.FrontBarWeapon.WeaponType = "Restoration Staff"

    candidates = service.build_candidates(
        build,
        character_id="char-1",
        baseline_build_id="build-1",
        active_bar="front",
        primary_per_objective=4,
        secondary_per_objective=4,
        mythic_per_objective=4,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    result = candidate.candidate_build
    assert candidate.changes[0].path == "Gear.FivePiecePlusFivePiecePlusRingMythic"
    assert all(
        result.Armor[slot]["Set"] == "Primary Healer"
        for slot in ("Chest", "Legs", "Hands", "Waist", "Feet")
    )
    assert result.Armor["Head"]["Set"] == "Secondary Healer"
    assert result.Armor["Shoulders"]["Set"] == "Secondary Healer"
    assert result.Necklace.Set == "Secondary Healer"
    assert result.FrontBarWeapon.Set == "Secondary Healer"
    assert result.FrontBarWeapon.WeaponType == "Restoration Staff"
    assert result.Ring1.Set == "Ring Mythic"
    assert build.Ring1.Set == ""
    assert build.FrontBarWeapon.Set == ""


def test_non_two_slot_or_aggregate_active_weapon_does_not_emit_package(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealMythicPackageService(database)

    sword = PlayerBuild(BuildName="Healer")
    sword.FrontBarWeapon.WeaponType = "Sword"
    assert service.build_candidates(
        sword,
        character_id="char-1",
        baseline_build_id="build-1",
        active_bar="front",
    ) == ()

    aggregate = PlayerBuild(BuildName="Healer")
    aggregate.FrontBarWeapon.WeaponType = "Two-Handed"
    assert service.build_candidates(
        aggregate,
        character_id="char-1",
        baseline_build_id="build-1",
        active_bar="front",
    ) == ()
