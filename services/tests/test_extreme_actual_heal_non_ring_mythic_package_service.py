from __future__ import annotations

import sqlite3
from pathlib import Path

from models.build_model import PlayerBuild
from services.extreme_actual_heal_non_ring_mythic_package_service import (
    ExtremeActualHealNonRingMythicPackageService,
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
                (1, 'Alpha Healer', 'standard', 5),
                (2, 'Beta Healer', 'standard', 5),
                (3, 'Shoulder Mythic', 'standard', 1),
                (4, 'Legs Mythic', 'standard', 1),
                (5, 'Neck Mythic', 'standard', 1),
                (6, 'Ring Mythic', 'standard', 1),
                (7, 'Weapon One Piece', 'standard', 1);

            INSERT INTO gear_set_bonus VALUES
                (1, 1, 5, 'Adds 171 Weapon and Spell Damage'),
                (2, 2, 5, 'Adds 171 Weapon and Spell Damage'),
                (3, 3, 1, 'Adds 171 Weapon and Spell Damage'),
                (4, 4, 1, 'Adds 171 Weapon and Spell Damage'),
                (5, 5, 1, 'Adds 171 Weapon and Spell Damage'),
                (6, 6, 1, 'Adds 171 Weapon and Spell Damage'),
                (7, 7, 1, 'Adds 171 Weapon and Spell Damage');
            """
        )
        for set_id in (1, 2):
            for equip_type in range(1, 10):
                armor_type = 1 if equip_type <= 7 else 0
                db.execute(
                    "INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES (?, ?, ?, 0)",
                    (set_id, equip_type, armor_type),
                )
            db.execute(
                "INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES (?, 11, 0, 9)",
                (set_id,),
            )
        db.executemany(
            "INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES (?, ?, ?, ?)",
            (
                (3, 4, 1, 0),
                (4, 6, 1, 0),
                (5, 8, 0, 0),
                (6, 9, 0, 0),
                (7, 11, 0, 9),
            ),
        )
        db.executemany(
            "INSERT INTO gear_set_item(set_id, item_id) VALUES (?, ?)",
            tuple((set_id, 1000 + set_id) for set_id in range(1, 8)),
        )


def test_discovers_non_ring_mythics_by_canonical_slot(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealNonRingMythicPackageService(database)

    mythics = service._reviewed_non_ring_mythics(per_objective=8)

    assert set(mythics) == {
        ("Shoulder Mythic", "Shoulders", 4),
        ("Legs Mythic", "Legs", 6),
        ("Neck Mythic", "Necklace", 8),
    }
    assert not any(name == "Ring Mythic" for name, _slot, _equip in mythics)
    assert not any(name == "Weapon One Piece" for name, _slot, _equip in mythics)


def test_assignment_routes_two_real_five_piece_sets_around_mythic_slot(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealNonRingMythicPackageService(database)

    assignment = service._assignment(
        "Alpha Healer",
        "Beta Healer",
        mythic_slot="Legs",
        weapon_type_id=9,
    )

    assert assignment is not None
    primary, secondary = assignment
    assert set(primary).isdisjoint(secondary)
    assert "Legs" not in primary
    assert "Legs" not in secondary
    weights = {position: count for position, _equip, count in service.NON_WEAPON_POSITIONS}
    weights["ActiveWeapon"] = 2
    assert sum(weights[position] for position in primary) == 5
    assert sum(weights[position] for position in secondary) == 5


def test_builds_packages_for_multiple_non_ring_mythic_slots(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealNonRingMythicPackageService(database)
    build = PlayerBuild(BuildName="Healer")
    build.FrontBarWeapon.WeaponType = "Restoration Staff"
    build.Ring2.Set = "Baseline Extra"

    candidates = service.build_candidates(
        build,
        character_id="char-1",
        baseline_build_id="build-1",
        active_bar="front",
        ordinary_per_objective=8,
        mythic_per_objective=8,
    )

    assert len(candidates) == 3
    by_slot = {
        candidate.changes[0].after["mythic_slot"]: candidate
        for candidate in candidates
    }
    assert set(by_slot) == {"Shoulders", "Legs", "Necklace"}

    for mythic_slot, candidate in by_slot.items():
        result = candidate.candidate_build
        change = candidate.changes[0]
        assert change.path == "Gear.FivePiecePlusFivePiecePlusSlotMythic"
        assert mythic_slot not in change.after["primary_positions"]
        assert mythic_slot not in change.after["secondary_positions"]
        if mythic_slot in result.Armor:
            assert result.Armor[mythic_slot]["Set"] == change.after["mythic"]
        elif mythic_slot == "Necklace":
            assert result.Necklace.Set == change.after["mythic"]

    assert build.Ring2.Set == "Baseline Extra"
    assert build.Armor["Shoulders"]["Set"] == ""
    assert build.Armor["Legs"]["Set"] == ""
    assert build.Necklace.Set == ""
