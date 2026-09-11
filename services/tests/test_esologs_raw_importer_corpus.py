from __future__ import annotations

import json
import sqlite3

from services.esologs_raw_importer import EsoLogsRawImporter


def _fight(fight_id: int, *, actor_id: int) -> dict:
    return {
        "metadata": {
            "id": fight_id,
            "name": "Lokkestiiz",
            "kill": True,
            "difficulty": 5,
            "bossPercentage": 0,
            "startTime": 1000,
            "endTime": 3000,
            "encounterID": 123,
        },
        "player_details": {
            "data": {
                "playerDetails": {
                    "healers": [
                        {
                            "id": actor_id,
                            "name": f"Healer {actor_id}",
                            "displayName": f"@healer{actor_id}",
                            "type": "Player",
                        }
                    ]
                }
            }
        },
        "event_count": 2,
        "events": [
            {
                "timestamp": 1000,
                "type": "damage",
                "sourceID": actor_id,
                "sourceIsFriendly": True,
                "targetID": 99,
                "targetIsFriendly": False,
                "abilityGameID": 7001,
                "amount": 100,
            },
            {
                "timestamp": 1001,
                "type": "heal",
                "sourceID": actor_id,
                "sourceIsFriendly": True,
                "targetID": actor_id,
                "targetIsFriendly": True,
                "abilityGameID": 9001,
                "ability": {"name": "Minor Lifesteal"},
                "amount": 600,
            },
        ],
    }


def test_imports_lokkestiiz_multi_report_corpus_envelope(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    payload = {
        "schema_version": 1,
        "encounter": "lokkestiiz",
        "reports": {
            "REPORT_A": {
                "matching_fight_count": 1,
                "fights": {"6": _fight(6, actor_id=7)},
            },
            "REPORT_B": {
                "matching_fight_count": 1,
                "fights": {"12": _fight(12, actor_id=8)},
            },
        },
    }
    (raw_dir / "lokkestiiz_corpus.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    connection = sqlite3.connect(tmp_path / "runtime.db")
    try:
        result = EsoLogsRawImporter(connection).import_directory(raw_dir)

        assert result == {
            "files": 1,
            "fights": 2,
            "actors": 2,
            "events": 4,
            "observed_windows": 2,
            "skipped": 0,
        }
        fight_rows = connection.execute(
            "SELECT report_code, fight_id FROM log_fight ORDER BY report_code"
        ).fetchall()
        assert [tuple(row) for row in fight_rows] == [
            ("REPORT_A", 6),
            ("REPORT_B", 12),
        ]
        assert connection.execute(
            "SELECT COUNT(*) FROM log_event"
        ).fetchone()[0] == 4
        manifest_rows = connection.execute(
            "SELECT report_code, record_count FROM log_import_manifest "
            "WHERE export_type = 'raw_probe_json' ORDER BY report_code"
        ).fetchall()
        assert [tuple(row) for row in manifest_rows] == [
            ("REPORT_A", 1),
            ("REPORT_B", 1),
        ]
    finally:
        connection.close()


def test_legacy_single_report_envelope_remains_supported(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    payload = {
        "report_code": "LEGACY",
        "fights": {"4": _fight(4, actor_id=11)},
    }
    (raw_dir / "legacy.json").write_text(json.dumps(payload), encoding="utf-8")

    connection = sqlite3.connect(tmp_path / "runtime.db")
    try:
        result = EsoLogsRawImporter(connection).import_directory(raw_dir)

        assert result["files"] == 1
        assert result["fights"] == 1
        assert result["events"] == 2
        row = connection.execute(
            "SELECT report_code, fight_id FROM log_fight"
        ).fetchone()
        assert tuple(row) == ("LEGACY", 4)
    finally:
        connection.close()
