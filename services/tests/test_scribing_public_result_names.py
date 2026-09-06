from __future__ import annotations

import sqlite3
from pathlib import Path

from services.scribing_result_service import ScribingResultService
from tools.import_scribing_result_names_from_esohub import parse_combination_page


def test_parse_public_combination_page() -> None:
    page = """
    <html><body>
      <h1>Warding Burst Skill - ESO</h1>
      <div>Name:</div><div>Warding Burst</div>
      <div>Combination:</div><div>Soul Burst and Damage Shield</div>
    </body></html>
    """
    row = parse_combination_page(
        page,
        54,
        "https://eso-hub.com/en/scribing/combination/54/warding-burst",
    )
    assert row is not None
    assert row.grimoire_name == "Soul Burst"
    assert row.focus_name == "Damage Shield"
    assert row.result_name == "Warding Burst"
    assert row.combination_id == 54


def test_service_falls_back_to_verified_public_reference(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE scribing_result_name_reference_source (
                source_key TEXT PRIMARY KEY,
                source_kind TEXT NOT NULL,
                source_url TEXT NOT NULL,
                probe_verified INTEGER NOT NULL DEFAULT 0,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE scribing_result_name_reference (
                source_key TEXT NOT NULL,
                grimoire_name TEXT NOT NULL,
                focus_name TEXT NOT NULL,
                result_name TEXT NOT NULL,
                combination_id INTEGER,
                page_url TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (source_key, grimoire_name, focus_name)
            );
            """
        )
        connection.execute(
            "INSERT INTO scribing_result_name_reference_source VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)",
            ("eso_hub:test", "public_web_reference", "https://eso-hub.com/en/scribing/combination"),
        )
        connection.execute(
            "INSERT INTO scribing_result_name_reference VALUES (?, ?, ?, ?, ?, ?)",
            (
                "eso_hub:test",
                "Soul Burst",
                "Damage Shield",
                "Warding Burst",
                54,
                "https://eso-hub.com/en/scribing/combination/54/warding-burst",
            ),
        )
        connection.commit()

    service = ScribingResultService(database)
    assert service.available is True
    assert service.source_kind == "public_web_reference"
    assert service.result_name("Soul Burst", "Damage Shield") == "Warding Burst"


def test_service_rejects_unverified_public_reference(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE scribing_result_name_reference_source (
                source_key TEXT PRIMARY KEY,
                source_kind TEXT NOT NULL,
                source_url TEXT NOT NULL,
                probe_verified INTEGER NOT NULL DEFAULT 0,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE scribing_result_name_reference (
                source_key TEXT NOT NULL,
                grimoire_name TEXT NOT NULL,
                focus_name TEXT NOT NULL,
                result_name TEXT NOT NULL,
                combination_id INTEGER,
                page_url TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (source_key, grimoire_name, focus_name)
            );
            """
        )
        connection.execute(
            "INSERT INTO scribing_result_name_reference_source VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)",
            ("eso_hub:test", "public_web_reference", "https://eso-hub.com/en/scribing/combination"),
        )
        connection.execute(
            "INSERT INTO scribing_result_name_reference VALUES (?, ?, ?, ?, ?, ?)",
            (
                "eso_hub:test",
                "Soul Burst",
                "Damage Shield",
                "Wrong Name",
                54,
                "https://eso-hub.com/en/scribing/combination/54/warding-burst",
            ),
        )
        connection.commit()

    service = ScribingResultService(database)
    assert service.available is False
    assert service.result_name("Soul Burst", "Damage Shield") == ""
