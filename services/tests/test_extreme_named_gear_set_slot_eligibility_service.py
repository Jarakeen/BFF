from __future__ import annotations

import sqlite3

from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)


def _database(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_piece (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER
            );
            CREATE TABLE content (
                id INTEGER PRIMARY KEY,
                content_type TEXT,
                name TEXT,
                location TEXT
            );
            CREATE TABLE content_sets (
                content_id INTEGER NOT NULL,
                set_id INTEGER NOT NULL
            );

            INSERT INTO gear_set(id, name, category, max_equip_count) VALUES
                (100, 'Ordinary Trial Set', 'Trial', 5),
                (200, 'Monster Set', 'Monster Set', 2),
                (300, 'Mythic Ring', 'Mythic', 1),
                (400, 'Arena Staff', 'Arena', 2);

            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES
                (100, 1, 2, 0),
                (100, 3, 2, 0),
                (100, 4, 2, 0),
                (100, 8, 2, 0),
                (100, 9, 2, 0),
                (100, 10, 2, 0),
                (100, 13, 2, 0),
                (100, 2, 0, 0),
                (100, 12, 0, 0),
                (200, 1, 1, 0),
                (200, 4, 1, 0),
                (300, 12, 0, 0),
                (400, 6, 0, 12);

            INSERT INTO content(id, content_type, name, location) VALUES
                (1, 'trial', 'Trial', ''),
                (2, 'dungeon', 'Dungeon', ''),
                (3, 'mythic', 'Antiquities', ''),
                (4, 'arena', 'Arena', '');
            INSERT INTO content_sets(content_id, set_id) VALUES
                (1, 100), (2, 200), (3, 300), (4, 400);
            """
        )


def test_exact_special_set_slots_are_preserved(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    catalog = ExtremeNamedGearSetSlotEligibilityService(path).build()

    monster = catalog.by_set_id(200)
    mythic = catalog.by_set_id(300)
    arena = catalog.by_set_id(400)

    assert monster is not None
    assert monster.armor_slots == ("Head", "Shoulders")
    assert monster.jewelry_slots == ()
    assert monster.weapon_types == ()

    assert mythic is not None
    assert mythic.jewelry_slots == ("Ring",)
    assert mythic.armor_slots == ()
    assert mythic.weapon_types == ()

    assert arena is not None
    assert arena.weapon_types == ("Inferno Staff",)
    assert arena.synthetic_weapon_types == ()


def test_standard_five_piece_set_recovers_reviewed_missing_weapon_shape(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    catalog = ExtremeNamedGearSetSlotEligibilityService(path).build()
    ordinary = catalog.by_set_id(100)

    assert ordinary is not None
    assert set(ordinary.armor_slots) == {
        "Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"
    }
    assert ordinary.jewelry_slots == ("Necklace", "Ring")
    assert len(ordinary.weapon_types) == 13
    assert len(ordinary.synthetic_weapon_types) == 13
    assert "Inferno Staff" in ordinary.weapon_types
    assert "Shield" in ordinary.weapon_types


def test_special_sets_do_not_receive_standard_weapon_synthesis(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    catalog = ExtremeNamedGearSetSlotEligibilityService(path).build()

    assert catalog.by_set_id(200).synthetic_weapon_types == ()
    assert catalog.by_set_id(300).synthetic_weapon_types == ()
    assert catalog.by_set_id(400).synthetic_weapon_types == ()


def test_complete_fixture_proves_named_set_slot_eligibility(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    catalog = ExtremeNamedGearSetSlotEligibilityService(path).build()

    assert catalog.unresolved == ()
    assert catalog.named_set_slot_eligibility_proven is True


def test_set_without_piece_rows_fails_closed(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (500, 'Mystery Set', 'Unknown', 5)"
        )
        connection.commit()

    catalog = ExtremeNamedGearSetSlotEligibilityService(path).build()

    assert catalog.named_set_slot_eligibility_proven is False
    assert catalog.by_set_id(500) is not None
    assert any("Mystery Set" in item and "no canonical gear_set_piece" in item for item in catalog.unresolved)


def test_unknown_weapon_type_fails_closed(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (600, 'Odd Weapon', 'Arena', 2)"
        )
        connection.execute(
            "INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES (600, 6, 0, 999)"
        )
        connection.commit()

    catalog = ExtremeNamedGearSetSlotEligibilityService(path).build()

    assert catalog.named_set_slot_eligibility_proven is False
    assert any("Odd Weapon" in item and "weapon_type 999" in item for item in catalog.unresolved)
