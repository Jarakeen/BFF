from __future__ import annotations

import sqlite3

from models.build_model import ARMOR_SLOTS, PlayerBuild
from services.extreme_actual_heal_armor_weight_legality_service import (
    ExtremeActualHealArmorWeightLegalityService,
)
from services.stickerbook_service import EQUIP_TYPES


def _equip_type(slot: str) -> int:
    matches = [
        int(key)
        for key, value in EQUIP_TYPES.items()
        if str(value).strip().casefold() == slot.casefold()
    ]
    assert len(matches) == 1
    return matches[0]


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            )
            """
        )
        db.execute(
            """
            CREATE TABLE gear_set_piece (
                set_id INTEGER NOT NULL,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER
            )
            """
        )
        db.executemany(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (?, ?, ?, ?)",
            (
                (1, "Light Only", "Overland", 5),
                (2, "All Weight Monster", "Monster", 2),
            ),
        )
        db.execute(
            "INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES (?, ?, ?, 0)",
            (1, _equip_type("Chest"), 1),
        )
        db.executemany(
            "INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES (?, ?, ?, 0)",
            tuple((2, _equip_type("Head"), armor_type) for armor_type in (1, 2, 3)),
        )
    return path


def _build() -> PlayerBuild:
    build = PlayerBuild(BuildName="Armor legality")
    for slot in ARMOR_SLOTS:
        build.Armor[slot]["Weight"] = "Medium"
    return build


def test_named_set_slot_rejects_impossible_saved_weight(tmp_path):
    database = _database(tmp_path)
    build = _build()
    build.Armor["Chest"]["Set"] = "Light Only"
    build.Armor["Chest"]["Weight"] = "Medium"

    result = ExtremeActualHealArmorWeightLegalityService(database).evaluate(build)
    chest = next(row for row in result.slots if row.slot == "Chest")

    assert chest.allowed_weights == ("Light",)
    assert chest.legal is False
    assert result.physically_legal is False
    assert any("Illegal armor weight" in item for item in result.unresolved)


def test_multiweight_named_piece_preserves_all_canonical_options(tmp_path):
    database = _database(tmp_path)
    build = _build()
    build.Armor["Head"]["Set"] = "All Weight Monster"
    build.Armor["Head"]["Weight"] = "Heavy"

    result = ExtremeActualHealArmorWeightLegalityService(database).evaluate(build)
    head = next(row for row in result.slots if row.slot == "Head")

    assert head.allowed_weights == ("Light", "Medium", "Heavy")
    assert head.legal is True
    assert result.physically_legal is True


def test_unset_armor_slots_allow_all_three_weights(tmp_path):
    database = _database(tmp_path)
    build = _build()

    result = ExtremeActualHealArmorWeightLegalityService(database).evaluate(build)

    assert result.physically_legal is True
    assert all(
        row.allowed_weights == ("Light", "Medium", "Heavy")
        for row in result.slots
    )


def test_unknown_named_set_fails_closed(tmp_path):
    database = _database(tmp_path)
    build = _build()
    build.Armor["Legs"]["Set"] = "Imaginary Pants"

    result = ExtremeActualHealArmorWeightLegalityService(database).evaluate(build)

    assert result.physically_legal is False
    assert any("not uniquely resolved canonically" in item for item in result.unresolved)
