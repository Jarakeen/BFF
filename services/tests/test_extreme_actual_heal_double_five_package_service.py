from __future__ import annotations

import sqlite3

from models.build_model import PlayerBuild
from services.extreme_actual_heal_double_five_package_service import (
    ExtremeActualHealDoubleFivePackageService,
)


def _write_structure(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
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
            CREATE TABLE gear_set_item (
                set_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                PRIMARY KEY(set_id, item_id)
            );

            INSERT INTO gear_set VALUES
                (1, 'Primary Five', 'standard', 5),
                (2, 'Secondary Five', 'standard', 5),
                (3, 'Missing Jewelry Family', 'standard', 5);

            -- The resolver already establishes imported Head=1 and Shoulders=4.
            -- The primary set proves five other distinct armor positions without
            -- requiring the optimizer to hard-code their numeric identities.
            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES
                (1, 2, 1, 0),
                (1, 3, 1, 0),
                (1, 5, 1, 0),
                (1, 6, 1, 0),
                (1, 7, 1, 0),

                (2, 1, 1, 0),
                (2, 4, 1, 0),
                (2, 20, 0, 0),
                (2, 21, 0, 0),

                (3, 1, 1, 0),
                (3, 4, 1, 0),
                (3, 20, 0, 0);

            INSERT INTO gear_set_item VALUES
                (1, 101),
                (2, 201),
                (2, 202),
                (3, 301);
            """
        )


def test_double_five_legality_uses_canonical_slot_structure(tmp_path):
    database = tmp_path / "eso.db"
    _write_structure(database)
    service = ExtremeActualHealDoubleFivePackageService(database)

    assert service._body_five_legal(1, "standard") is True
    assert service._head_shoulders_jewelry_legal(2, "standard") is True
    assert service._head_shoulders_jewelry_legal(3, "standard") is False


def test_double_five_candidate_materializes_ten_real_slots_without_mutating_baseline():
    service = ExtremeActualHealDoubleFivePackageService.__new__(
        ExtremeActualHealDoubleFivePackageService
    )
    service._reviewed_names = lambda *, secondary_shape, per_objective: (
        ("Secondary Five",) if secondary_shape else ("Primary Five",)
    )

    baseline = PlayerBuild(BuildName="Healer")
    for slot in baseline.Armor.values():
        slot["Set"] = "Old Armor Set"
    baseline.Necklace.Set = "Old Jewelry Set"
    baseline.Ring1.Set = "Old Jewelry Set"
    baseline.Ring2.Set = "Old Jewelry Set"

    candidates = service.build_candidates(
        baseline,
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    build = candidate.candidate_build
    assert candidate.changes[0].path == "Gear.FivePiecePlusFivePiece"
    assert all(
        build.Armor[slot]["Set"] == "Primary Five"
        for slot in service.BODY_FIVE_SLOTS
    )
    assert build.Armor["Head"]["Set"] == "Secondary Five"
    assert build.Armor["Shoulders"]["Set"] == "Secondary Five"
    assert build.Necklace.Set == "Secondary Five"
    assert build.Ring1.Set == "Secondary Five"
    assert build.Ring2.Set == "Secondary Five"

    assert all(slot["Set"] == "Old Armor Set" for slot in baseline.Armor.values())
    assert baseline.Necklace.Set == "Old Jewelry Set"
    assert baseline.Ring1.Set == "Old Jewelry Set"
    assert baseline.Ring2.Set == "Old Jewelry Set"


def test_double_five_package_never_uses_same_set_twice():
    service = ExtremeActualHealDoubleFivePackageService.__new__(
        ExtremeActualHealDoubleFivePackageService
    )
    service._reviewed_names = lambda *, secondary_shape, per_objective: ("Same Set",)

    assert service.build_candidates(
        PlayerBuild(BuildName="Healer"),
        character_id="char-1",
        baseline_build_id="build-1",
    ) == ()
