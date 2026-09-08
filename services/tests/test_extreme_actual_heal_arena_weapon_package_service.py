from __future__ import annotations

import sqlite3
from pathlib import Path

from models.build_model import PlayerBuild
from services.extreme_actual_heal_arena_weapon_package_service import (
    ExtremeActualHealArenaWeaponPackageService,
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
            CREATE TABLE gear_set_piece (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER
            );

            INSERT INTO gear_set VALUES
                (1, 'Resto Arena', 'standard', 2),
                (2, 'Inferno Arena', 'standard', 2),
                (3, 'Ordinary Five', 'standard', 5),
                (4, 'Monster Pair', 'monster', 2),
                (5, 'Mixed Pair', 'standard', 2);

            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES
                (1, 11, 0, 9),
                (2, 11, 0, 12),
                (3, 11, 0, 9),
                (4, 1, 1, 0),
                (4, 4, 1, 0),
                (5, 11, 0, 9),
                (5, 8, 0, 0);
            """
        )


def test_exact_active_weapon_subtype_filters_arena_sets(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealArenaWeaponPackageService(database)

    assert service._matching_sets(9) == ("Resto Arena",)
    assert service._matching_sets(12) == ("Inferno Arena",)


def test_builds_real_active_arena_weapon_candidate_without_changing_weapon_type(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealArenaWeaponPackageService(database)
    build = PlayerBuild(BuildName="Healer")
    build.FrontBarWeapon.WeaponType = "Restoration Staff"
    build.FrontBarWeapon.Set = "Old Set"

    candidates = service.build_candidates(
        build,
        character_id="char-1",
        baseline_build_id="build-1",
        active_bar="front",
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    result = candidate.candidate_build
    assert candidate.changes[0].path == "Gear.ArenaWeapon"
    assert result.FrontBarWeapon.Set == "Resto Arena"
    assert result.FrontBarWeapon.Set2 == ""
    assert result.FrontBarWeapon.WeaponType == "Restoration Staff"
    assert build.FrontBarWeapon.Set == "Old Set"


def test_ambiguous_or_paired_active_weapon_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _write_db(database)
    service = ExtremeActualHealArenaWeaponPackageService(database)

    ambiguous = PlayerBuild(BuildName="Healer")
    ambiguous.FrontBarWeapon.WeaponType = "Two-Handed"
    assert service.build_candidates(
        ambiguous,
        character_id="char-1",
        baseline_build_id="build-1",
    ) == ()

    paired = PlayerBuild(BuildName="Healer")
    paired.FrontBarWeapon.WeaponType = "Sword"
    paired.FrontBarOffhand.WeaponType = "Shield"
    assert service.build_candidates(
        paired,
        character_id="char-1",
        baseline_build_id="build-1",
    ) == ()
