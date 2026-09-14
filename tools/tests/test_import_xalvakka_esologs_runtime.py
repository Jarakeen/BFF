import sqlite3

from services.esologs_importer import EsoLogsImporter
from tools.import_xalvakka_esologs_runtime import (
    persist_report_metadata,
    select_xalvakka_fights,
)


def _fight(fight_id, name, *, kill=True, difficulty=121, boss_percentage=0):
    return {
        "id": fight_id,
        "name": name,
        "kill": kill,
        "difficulty": difficulty,
        "bossPercentage": boss_percentage,
        "startTime": float(fight_id * 1000),
        "endTime": float(fight_id * 1000 + 500),
        "encounterID": 999,
    }


def test_selects_only_exact_xalvakka_fights_and_preserves_repeated_pulls():
    fights = [
        _fight(1, "Oaxiltso"),
        _fight(2, "Xalvakka", kill=False, boss_percentage=7000),
        _fight(3, " xalvakka ", kill=True),
        _fight(4, "Xalvakka Add"),
    ]

    selected = select_xalvakka_fights(fights)

    assert [fight["id"] for fight in selected] == [2, 3]


def test_persist_report_metadata_keeps_only_selected_xalvakka_rows(tmp_path):
    path = tmp_path / "xalvakka.db"
    with sqlite3.connect(path) as connection:
        # Build the canonical metadata schema, then exercise the focused writer.
        EsoLogsImporter(connection, client=None)  # type: ignore[arg-type]
        fights = (
            _fight(8, "Xalvakka", kill=False, boss_percentage=3912),
            _fight(11, "Xalvakka", kill=True, boss_percentage=0),
        )
        persist_report_metadata(connection, report_code="ABC123", fights=fights)

        report = connection.execute(
            "SELECT report_code, source_url FROM log_report"
        ).fetchone()
        rows = connection.execute(
            "SELECT fight_id, name, kill, boss_percentage FROM log_fight ORDER BY fight_id"
        ).fetchall()

    assert report == ("ABC123", "https://www.esologs.com/reports/ABC123")
    assert rows == [
        (8, "Xalvakka", 0, 3912.0),
        (11, "Xalvakka", 1, 0.0),
    ]
