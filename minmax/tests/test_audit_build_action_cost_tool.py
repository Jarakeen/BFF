from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "audit_build_action_cost.py"


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE ability (
                id INTEGER PRIMARY KEY,
                ability_id INTEGER,
                name TEXT,
                rank INTEGER,
                morph INTEGER,
                base_cost REAL,
                base_mechanic INTEGER,
                skill_line TEXT
            );
            CREATE TABLE jewelry_glyph (
                item_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE jewelry_glyph_effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                glyph_item_id INTEGER NOT NULL,
                effect_type TEXT,
                value_min REAL,
                value_max REAL,
                unit TEXT,
                description TEXT
            );
            """
        )
        connection.executemany(
            "INSERT INTO ability VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (99, 41189, "Combat Prayer", 4, 2, 4590, 1, "Restoration Staff"),
                (100, 1001, "Echoing Vigor", 1, 1, 3200, 4, "Assault"),
                (101, 1004, "Echoing Vigor", 4, 1, 2980, 4, "Assault"),
            ],
        )
        connection.execute(
            "INSERT INTO jewelry_glyph VALUES (?, ?)",
            (1, "Glyph of Reduce Spell Cost"),
        )
        connection.execute(
            """
            INSERT INTO jewelry_glyph_effect(
                glyph_item_id, effect_type, value_min, value_max, unit, description
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (1, "magicka_cost_reduction", 203, 203, "flat", "magicka"),
        )
    return path


def _builds(tmp_path: Path) -> Path:
    path = tmp_path / "builds.json"
    armor = {
        slot: {"Weight": "Light" if slot != "Head" else "Medium"}
        for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
    }
    payload = {
        "Members": [
            {
                "Name": "Magrat",
                "BuildName": "DF Healer",
                "Race": "Breton",
                "Armor": armor,
                "Necklace": {
                    "Enchant": "Reduce Spell Cost",
                    "Trait": "Swift",
                    "Quality": "Gold",
                    "EnchantTier": "Truly Superb",
                    "Level": "CP160",
                },
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_tool_prints_modifier_breakdown_and_final_cost(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--build",
            "DF Healer",
            "--ability-id",
            "41189",
            "--database",
            str(_database(tmp_path)),
            "--builds",
            str(_builds(tmp_path)),
            "--owned-skill-line",
            "Light Armor",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Ability ID:     41189" in result.stdout
    assert "Breton: Magicka Mastery" in result.stdout
    assert "Light Armor: Evocation (6 pieces; live verified)" in result.stdout
    assert "Necklace: Glyph of Reduce Spell Cost" in result.stdout
    assert "magicka: base=4590 flat=203 percent=0.18" in result.stdout
    assert "final=3597" in result.stdout


def test_tool_resolves_exact_name_to_unique_highest_rank(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--build",
            "DF Healer",
            "--name",
            "Echoing Vigor",
            "--database",
            str(_database(tmp_path)),
            "--builds",
            str(_builds(tmp_path)),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Ability:        Echoing Vigor" in result.stdout
    assert "Ability ID:     1004" in result.stdout
    assert "Rank / morph:   4 / 1" in result.stdout
    assert "Base cost:      2980" in result.stdout
    assert "Resources:      stamina" in result.stdout


def test_tool_fails_explicitly_for_missing_build(tmp_path: Path) -> None:
    database = _database(tmp_path)
    builds = _builds(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--build",
            "Missing Build",
            "--ability-id",
            "41189",
            "--database",
            str(database),
            "--builds",
            str(builds),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Saved build not found: Missing Build" in result.stderr
