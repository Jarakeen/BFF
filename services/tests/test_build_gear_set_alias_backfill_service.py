from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from services.build_gear_set_alias_backfill_service import backfill_saved_build_gear_aliases


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE gear_set (id INTEGER PRIMARY KEY, name TEXT, category TEXT, max_equip_count INTEGER)"
        )
        connection.executemany(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (?, ?, ?, ?)",
            [
                (1, "Roaring Opportunist", "Trial", 5),
                (2, "Perfected Roaring Opportunist", "Trial", 5),
                (3, "Pillager's Profit", "Dungeon", 5),
                (4, "Symphony of Blades", "Monster", 2),
                (5, "Ozezan the Inferno", "Monster", 2),
                (6, "Lucent Echoes", "Trial", 5),
            ],
        )
    return path


def test_backfill_repairs_only_recognized_old_shorthand_and_creates_backup(tmp_path: Path) -> None:
    db = _database(tmp_path)
    builds = tmp_path / "builds.json"
    payload = {
        "Members": [
            {
                "Name": "Magrat",
                "BuildName": "Imported Healer",
                "Armor": {
                    "Head": {"Set": "SoB"},
                    "Chest": {"Set": "RO"},
                    "Hands": {"Set": "Roaring Opportunist"},
                },
                "FrontBarWeapon": {"Set": "Pill"},
                "ContextVariants": [
                    {"Armor": {"Shoulders": {"Set": "Oz"}}, "Necklace": {"Set": "LE"}}
                ],
            }
        ]
    }
    builds.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    report = backfill_saved_build_gear_aliases(builds, db)

    repaired = json.loads(builds.read_text(encoding="utf-8"))["Members"][0]
    assert repaired["Armor"]["Head"]["Set"] == "Symphony of Blades"
    assert repaired["Armor"]["Chest"]["Set"] == "Perfected Roaring Opportunist"
    # Full canonical non-Perfected names are intentionally left alone by repair.
    assert repaired["Armor"]["Hands"]["Set"] == "Roaring Opportunist"
    assert repaired["FrontBarWeapon"]["Set"] == "Pillager's Profit"
    assert repaired["ContextVariants"][0]["Armor"]["Shoulders"]["Set"] == "Ozezan the Inferno"
    assert repaired["ContextVariants"][0]["Necklace"]["Set"] == "Lucent Echoes"
    assert report.changed_values == 5
    assert report.changed_builds == 1
    assert report.backup_path is not None
    assert report.backup_path.exists()


def test_backfill_is_idempotent(tmp_path: Path) -> None:
    db = _database(tmp_path)
    builds = tmp_path / "builds.json"
    builds.write_text(
        json.dumps({"Members": [{"Name": "Rik", "BuildName": "Tank", "Armor": {"Chest": {"Set": "RO"}}}]}),
        encoding="utf-8",
    )
    first = backfill_saved_build_gear_aliases(builds, db)
    second = backfill_saved_build_gear_aliases(builds, db)
    assert first.changed_values == 1
    assert second.changed_values == 0
    assert second.backup_path is None
