from __future__ import annotations

import sqlite3

from services.esologs_importer import EsoLogsImporter


class FakeEsoLogsClient:
    def get_fights(self, report_code: str) -> list[dict]:
        assert report_code == "ABC123"
        return [
            {
                "id": 7,
                "name": "Test Boss",
                "kill": True,
                "difficulty": 5,
                "bossPercentage": 0,
                "startTime": 1000,
                "endTime": 6000,
                "encounterID": 42,
            }
        ]

    def get_aura_table(
        self,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
        data_type: str = "Buffs",
        hostility_type: str = "Friendlies",
        source_id: int | None = None,
    ) -> list[dict]:
        return [
            {
                "name": f"{data_type} Example",
                "guid": 1234,
                "totalUptime": 5000,
                "totalUses": 3,
            }
        ]


def test_import_creates_manifest_and_records() -> None:
    connection = sqlite3.connect(":memory:")
    importer = EsoLogsImporter(connection, FakeEsoLogsClient())

    result = importer.import_report("ABC123")

    assert result == {"fights": 1, "auras": 2}
    assert connection.execute("select count(*) from log_fight").fetchone()[0] == 1
    assert connection.execute("select count(*) from log_aura").fetchone()[0] == 2

    rows = connection.execute(
        """
        select export_name, export_type, source_url, status,
               record_count, destination_tables
        from log_import_manifest
        order by id
        """
    ).fetchall()

    assert len(rows) == 3
    assert rows[0][0] == "report_fights"
    assert rows[0][1] == "fights"
    assert rows[0][2] == "https://www.esologs.com/reports/ABC123"
    assert rows[0][3] == "imported"
    assert rows[0][4] == 1
    assert rows[0][5] == '["log_report", "log_fight"]'
    assert all(row[3] == "imported" for row in rows)
    assert sum(row[4] for row in rows) == 3
