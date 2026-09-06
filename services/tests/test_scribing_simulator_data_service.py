from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from services.scribing_simulator_data_service import ScribingSimulatorDataService


def _database(path: Path) -> Path:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE scribing_result_name_reference_source (
                source_key TEXT PRIMARY KEY,
                source_kind TEXT NOT NULL,
                source_url TEXT NOT NULL,
                probe_verified INTEGER NOT NULL DEFAULT 0,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE scribing_simulator_script (
                source_key TEXT NOT NULL,
                script_id INTEGER NOT NULL,
                script_type INTEGER NOT NULL,
                name TEXT NOT NULL,
                icon TEXT NOT NULL DEFAULT '',
                is_class_specific INTEGER NOT NULL DEFAULT 0,
                raw_json TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (source_key, script_id)
            );
            CREATE TABLE scribing_simulator_skill (
                source_key TEXT NOT NULL,
                skill_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                icon TEXT NOT NULL DEFAULT '',
                scripts_json TEXT NOT NULL DEFAULT '[]',
                forbidden_combinations_json TEXT NOT NULL DEFAULT '[]',
                raw_json TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (source_key, skill_id)
            );
            """
        )
        source = ScribingSimulatorDataService.SOURCE_KEY
        connection.execute(
            """
            INSERT INTO scribing_result_name_reference_source(
                source_key, source_kind, source_url, probe_verified
            ) VALUES (?, 'public_simulator_api', 'https://example.invalid', 1)
            """,
            (source,),
        )
        connection.executemany(
            """
            INSERT INTO scribing_simulator_script(
                source_key, script_id, script_type, name
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (source, 101, 1, "Magic Damage"),
                (source, 201, 2, "Lingering Torment"),
                (source, 202, 2, "Class Flourish"),
                (source, 301, 3, "Breach"),
                (source, 302, 3, "Heroism"),
            ],
        )
        connection.execute(
            """
            INSERT INTO scribing_simulator_skill(
                source_key, skill_id, name, scripts_json,
                forbidden_combinations_json
            ) VALUES (?, 7, 'Wield Soul', ?, ?)
            """,
            (
                source,
                json.dumps([101, 201, 202, 301, 302]),
                json.dumps([[101, 201, 302], {"scripts": [101, 202, 301]}]),
            ),
        )
        connection.commit()
    return path


def test_structured_choices_and_forbidden_combinations(tmp_path: Path) -> None:
    service = ScribingSimulatorDataService(_database(tmp_path / "eso.db"))

    assert service.available is True
    assert service.compatible_focus("Wield Soul") == ["Magic Damage"]
    assert service.compatible_signature("Wield Soul") == ["Class Flourish", "Lingering Torment"]
    assert service.compatible_affix("Wield Soul") == ["Breach", "Heroism"]

    assert service.is_combination_allowed(
        "Wield Soul", ["Magic Damage", "Lingering Torment", "Breach"]
    ) is True
    assert service.is_combination_allowed(
        "Wield Soul", ["Magic Damage", "Lingering Torment", "Heroism"]
    ) is False
    assert service.is_combination_allowed(
        "Wield Soul", ["Magic Damage", "Class Flourish", "Breach"]
    ) is False


def test_filtered_choices_remove_forbidden_third_script(tmp_path: Path) -> None:
    service = ScribingSimulatorDataService(_database(tmp_path / "eso.db"))

    assert service.filtered_choices(
        "Wield Soul",
        3,
        ["Magic Damage", "Lingering Torment"],
    ) == ["Breach"]
