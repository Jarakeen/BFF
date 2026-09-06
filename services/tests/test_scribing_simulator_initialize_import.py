from __future__ import annotations

import sqlite3
from pathlib import Path

from services.scribing_result_service import ScribingResultService
from tools.import_scribing_simulator_initialize import (
    SOURCE_KEY,
    extract_result_pairs,
    import_payload,
)


def _payload() -> dict:
    return {
        "classes": [],
        "scripts": [
            {"id": 101, "name": "Damage Shield", "type": 1, "icon": "focus.dds"},
            {"id": 201, "name": "Class Flourish", "type": 2, "icon": "sig.dds"},
            {"id": 301, "name": "Courage", "type": 3, "icon": "affix.dds"},
        ],
        "skills": [
            {
                "id": 54,
                "name": "Soul Burst",
                "icon": "soulburst.dds",
                "scripts": [101, 201, 301],
                "scripts_forbidden_combinations": [[101, 201, 301]],
                "variations": {
                    "101": {
                        "name": "Warding Burst",
                        "description": "Create a protective burst.",
                        "cost": "3510 Magicka",
                    }
                },
            }
        ],
    }


def test_extracts_focus_variation_result_name() -> None:
    rows = extract_result_pairs(_payload())
    assert len(rows) == 1
    row = rows[0]
    assert row.grimoire_name == "Soul Burst"
    assert row.focus_name == "Damage Shield"
    assert row.result_name == "Warding Burst"


def test_imports_structured_simulator_reference(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as connection:
        counts = import_payload(connection, _payload())

    assert counts == (3, 1, 1, 1, True)

    with sqlite3.connect(database) as connection:
        source = connection.execute(
            "SELECT source_kind, probe_verified FROM scribing_result_name_reference_source WHERE source_key = ?",
            (SOURCE_KEY,),
        ).fetchone()
        variation = connection.execute(
            """
            SELECT result_name, description, cost
            FROM scribing_simulator_variation
            WHERE source_key = ? AND skill_id = 54 AND focus_script_id = 101
            """,
            (SOURCE_KEY,),
        ).fetchone()
        skill = connection.execute(
            "SELECT forbidden_combinations_json FROM scribing_simulator_skill WHERE source_key = ? AND skill_id = 54",
            (SOURCE_KEY,),
        ).fetchone()

    assert source == ("public_simulator_api", 1)
    assert variation == ("Warding Burst", "Create a protective burst.", "3510 Magicka")
    assert skill is not None and "101" in skill[0]


def test_service_prefers_structured_public_feed(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as connection:
        import_payload(connection, _payload())
        connection.execute(
            """
            INSERT INTO scribing_result_name_reference_source(
                source_key, source_kind, source_url, probe_verified, imported_at
            ) VALUES ('older-crawl', 'public_web_reference', 'https://example.invalid', 1, '2099-01-01 00:00:00')
            """
        )
        connection.execute(
            """
            INSERT INTO scribing_result_name_reference(
                source_key, grimoire_name, focus_name, result_name, combination_id, page_url
            ) VALUES ('older-crawl', 'Soul Burst', 'Damage Shield', 'Wrong Newer Crawl Name', 54, '')
            """
        )
        connection.commit()

    service = ScribingResultService(database)
    assert service.source_kind == "public_simulator_api"
    assert service.result_name("Soul Burst", "Damage Shield") == "Warding Burst"
