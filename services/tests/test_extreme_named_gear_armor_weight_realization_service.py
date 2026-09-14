from __future__ import annotations

import sqlite3

from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_named_gear_armor_weight_realization_service import (
    ExtremeNamedGearArmorWeightRealizationService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)


_ALL_ARMOR = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
_ALL_WEAPONS = (
    "Axe", "Mace", "Sword", "Dagger", "Shield",
    "Two-Handed Sword", "Two-Handed Axe", "Two-Handed Mace",
    "Bow", "Restoration Staff", "Inferno Staff", "Ice Staff", "Lightning Staff",
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


def _ordinary(set_id: int, name: str) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="Trial",
        max_equip_count=5,
        armor_slots=_ALL_ARMOR,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=_ALL_WEAPONS,
    )


def _monster(set_id: int, name: str) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="Monster Set",
        max_equip_count=2,
        armor_slots=("Head", "Shoulders"),
    )


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


def _armor_rows(set_id: int, weight: int):
    return tuple(
        (set_id, _EQUIP_IDS[slot], weight, 0)
        for slot in _ALL_ARMOR
    )


def test_five_five_two_can_prove_seven_heavy_named_set_witness(tmp_path):
    path = tmp_path / "eso.db"
    _database(
        path,
        (
            *_armor_rows(10, 3),
            *_armor_rows(20, 3),
            (30, _EQUIP_IDS["Head"], 3, 0),
            (30, _EQUIP_IDS["Shoulders"], 3, 0),
        ),
    )
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)
    named_sets = (_ordinary(10, "Five A"), _ordinary(20, "Five B"), _monster(30, "Monster"))

    result = ExtremeNamedGearArmorWeightRealizationService(path).find_witness(
        topology,
        named_sets,
        required_armor_weight="Heavy",
    )

    assert result.compatible is True
    assert result.witness is not None
    armor_assignments = tuple(
        row for row in result.witness.body_jewelry_assignments if row.slot in _ALL_ARMOR
    )
    assert len(armor_assignments) == 7


def test_light_only_monster_blocks_seven_heavy_even_when_generic_slots_fit(tmp_path):
    path = tmp_path / "eso.db"
    _database(
        path,
        (
            *_armor_rows(10, 3),
            *_armor_rows(20, 3),
            (30, _EQUIP_IDS["Head"], 1, 0),
            (30, _EQUIP_IDS["Shoulders"], 1, 0),
        ),
    )
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)
    named_sets = (_ordinary(10, "Five A"), _ordinary(20, "Five B"), _monster(30, "Monster"))

    assert ExtremeNamedGearSetRealizationService.find_witness(topology, named_sets) is not None
    result = ExtremeNamedGearArmorWeightRealizationService(path).find_witness(
        topology,
        named_sets,
        required_armor_weight="Heavy",
    )

    assert result.compatible is False
    assert result.witness is None
    assert result.unresolved == ()


def test_both_monster_slots_must_support_required_weight(tmp_path):
    path = tmp_path / "eso.db"
    _database(
        path,
        (
            (30, _EQUIP_IDS["Head"], 3, 0),
            (30, _EQUIP_IDS["Shoulders"], 1, 0),
        ),
    )
    topology = ExtremeGearSetCountTopology(counts=(2,), unused_units=10)

    result = ExtremeNamedGearArmorWeightRealizationService(path).find_witness(
        topology,
        (_monster(30, "Mixed Monster"),),
        required_armor_weight="Heavy",
    )

    assert result.compatible is False


def test_non_heavy_five_piece_set_can_avoid_armor_via_jewelry_and_weapon_slots(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, _armor_rows(10, 2))
    topology = ExtremeGearSetCountTopology(counts=(5,), unused_units=7)
    named = _ordinary(10, "Medium Five")

    result = ExtremeNamedGearArmorWeightRealizationService(path).find_witness(
        topology,
        (named,),
        required_armor_weight="Heavy",
    )

    assert result.compatible is True
    assert result.witness is not None
    assert not any(
        row.slot in _ALL_ARMOR for row in result.witness.body_jewelry_assignments
    )
    assert len(result.witness.weapon_assignments) == 2
    assert {row.slot for row in result.witness.weapon_assignments} == {
        "Main Hand",
        "Off Hand",
    }


def test_missing_database_evidence_fails_closed(tmp_path):
    missing = tmp_path / "missing.db"
    topology = ExtremeGearSetCountTopology(counts=(2,), unused_units=10)

    result = ExtremeNamedGearArmorWeightRealizationService(missing).find_witness(
        topology,
        (_monster(30, "Monster"),),
        required_armor_weight="Heavy",
    )

    assert result.compatible is False
    assert result.witness is None
    assert result.unresolved


def test_unknown_requested_weight_fails_closed(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, ((30, _EQUIP_IDS["Head"], 3, 0),))
    topology = ExtremeGearSetCountTopology(counts=(1,), unused_units=11)

    result = ExtremeNamedGearArmorWeightRealizationService(path).find_witness(
        topology,
        (_monster(30, "Monster"),),
        required_armor_weight="Adamantium",
    )

    assert result.compatible is False
    assert result.unresolved == ("Unknown required armor weight: 'Adamantium'",)
