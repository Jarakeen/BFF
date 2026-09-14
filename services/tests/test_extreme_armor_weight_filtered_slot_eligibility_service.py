from __future__ import annotations

import sqlite3

from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


_EQUIP_IDS = {
    "Head": 1,
    "Necklace": 2,
    "Chest": 3,
    "Shoulders": 4,
    "Waist": 8,
    "Legs": 9,
    "Feet": 10,
    "Ring": 12,
    "Hands": 13,
}
_BODY = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")


def _database(path, rows):
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE gear_set_piece (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )


def _row(set_id: int, name: str) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="Trial",
        max_equip_count=5,
        armor_slots=_BODY,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=("Axe", "Restoration Staff"),
    )


def test_filter_keeps_only_slots_supporting_requested_weight(tmp_path):
    path = tmp_path / "eso.db"
    _database(
        path,
        (
            (10, _EQUIP_IDS["Head"], 3, 0),
            (10, _EQUIP_IDS["Shoulders"], 1, 0),
            (10, _EQUIP_IDS["Chest"], 3, 0),
        ),
    )
    catalog = ExtremeNamedGearSetSlotEligibilityCatalog(sets=(_row(10, "Mixed"),))

    result = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        path,
        catalog,
        required_armor_weight="Heavy",
    )

    assert result.denominator_proven is True
    filtered = result.catalog.sets[0]
    assert filtered.armor_slots == ("Head", "Chest")
    assert filtered.jewelry_slots == ("Necklace", "Ring")
    assert filtered.weapon_types == ("Axe", "Restoration Staff")


def test_medium_only_set_can_still_use_jewelry_and_weapons_in_heavy_search(tmp_path):
    path = tmp_path / "eso.db"
    rows = tuple((10, _EQUIP_IDS[slot], 2, 0) for slot in _BODY)
    _database(path, rows)
    catalog = ExtremeNamedGearSetSlotEligibilityCatalog(sets=(_row(10, "Medium Set"),))

    result = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        path,
        catalog,
        required_armor_weight="Heavy",
    )

    filtered = result.catalog.sets[0]
    assert filtered.armor_slots == ()
    assert filtered.jewelry_slots == ("Necklace", "Ring")
    assert filtered.weapon_types == ("Axe", "Restoration Staff")


def test_upstream_catalog_diagnostic_does_not_poison_filter_proof(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, tuple((10, _EQUIP_IDS[slot], 3, 0) for slot in _BODY))
    catalog = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=(_row(10, "Heavy Set"),),
        unresolved=("unrelated upstream slot-catalog diagnostic",),
    )

    result = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        path,
        catalog,
        required_armor_weight="Heavy",
    )

    assert result.denominator_proven is True
    assert result.unresolved == ()
    assert result.catalog.unresolved == ("unrelated upstream slot-catalog diagnostic",)


def test_missing_armor_weight_evidence_fails_closed(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, ())
    catalog = ExtremeNamedGearSetSlotEligibilityCatalog(sets=(_row(10, "Unknown"),))

    result = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        path,
        catalog,
        required_armor_weight="Heavy",
    )

    assert result.denominator_proven is False
    assert result.unresolved


def test_unknown_weight_fails_closed(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, ())
    catalog = ExtremeNamedGearSetSlotEligibilityCatalog(sets=(_row(10, "Unknown"),))

    result = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        path,
        catalog,
        required_armor_weight="Adamantium",
    )

    assert result.denominator_proven is False
    assert result.unresolved == ("Unknown required armor weight: 'Adamantium'",)
