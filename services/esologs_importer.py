from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from services.esologs_client import EsoLogsClient


REPORT_URL = "https://www.esologs.com/reports/{report_code}"
GRAPHQL_URL = "https://www.esologs.com/api/v2/client"


class EsoLogsImporter:
    """Import ESO Logs report exports into SQLite with provenance."""

    def __init__(self, connection: sqlite3.Connection, client: EsoLogsClient):
        self.connection = connection
        self.client = client
        self.connection.row_factory = sqlite3.Row
        self.ensure_schema()

    def ensure_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS log_import_manifest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                export_name TEXT NOT NULL,
                export_type TEXT NOT NULL,
                report_code TEXT,
                fetched_at TEXT NOT NULL,
                source_url TEXT NOT NULL,
                request_json TEXT,
                status TEXT NOT NULL,
                record_count INTEGER NOT NULL DEFAULT 0,
                destination_tables TEXT NOT NULL,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS log_report (
                report_code TEXT PRIMARY KEY,
                title TEXT,
                source_url TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS log_fight (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                name TEXT,
                kill INTEGER,
                difficulty INTEGER,
                boss_percentage REAL,
                start_time REAL,
                end_time REAL,
                encounter_id INTEGER,
                raw_json TEXT NOT NULL,
                PRIMARY KEY (report_code, fight_id),
                FOREIGN KEY (report_code) REFERENCES log_report(report_code)
            );

            CREATE TABLE IF NOT EXISTS log_aura (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                data_type TEXT NOT NULL,
                hostility_type TEXT NOT NULL,
                source_id INTEGER NOT NULL DEFAULT -1,
                aura_name TEXT,
                aura_guid INTEGER,
                total_uptime REAL,
                total_uses INTEGER,
                raw_json TEXT NOT NULL,
                PRIMARY KEY (
                    report_code,
                    fight_id,
                    data_type,
                    hostility_type,
                    source_id,
                    aura_name,
                    aura_guid
                ),
                FOREIGN KEY (report_code, fight_id)
                    REFERENCES log_fight(report_code, fight_id)
            );

            CREATE INDEX IF NOT EXISTS idx_log_fight_report
                ON log_fight(report_code);
            CREATE INDEX IF NOT EXISTS idx_log_aura_fight
                ON log_aura(report_code, fight_id);
            """
        )
        self.connection.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    def _manifest_start(
        self,
        *,
        export_name: str,
        export_type: str,
        report_code: str,
        request: dict[str, Any],
        destination_tables: list[str],
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO log_import_manifest (
                export_name,
                export_type,
                report_code,
                fetched_at,
                source_url,
                request_json,
                status,
                record_count,
                destination_tables
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                export_name,
                export_type,
                report_code,
                self._now(),
                REPORT_URL.format(report_code=report_code),
                self._json(request),
                "started",
                0,
                self._json(destination_tables),
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def _manifest_finish(
        self,
        manifest_id: int,
        *,
        status: str,
        record_count: int,
        error_message: str | None = None,
    ) -> None:
        self.connection.execute(
            """
            UPDATE log_import_manifest
            SET status = ?, record_count = ?, error_message = ?
            WHERE id = ?
            """,
            (status, record_count, error_message, manifest_id),
        )
        self.connection.commit()

    def import_report(self, report_code: str) -> dict[str, int]:
        """Fetch and import the report's fights and aura exports."""
        report_code = report_code.strip()
        if not report_code:
            raise ValueError("report_code must not be empty")

        report_url = REPORT_URL.format(report_code=report_code)
        fights_manifest = self._manifest_start(
            export_name="report_fights",
            export_type="fights",
            report_code=report_code,
            request={"query": "ReportFights", "report_code": report_code},
            destination_tables=["log_report", "log_fight"],
        )

        try:
            fights = self.client.get_fights(report_code)
            fetched_at = self._now()
            title = None
            if fights:
                # ESO Logs returns report title separately from fights in the
                # client today; keep this nullable rather than making up data.
                title = None

            self.connection.execute(
                """
                INSERT INTO log_report (
                    report_code, title, source_url, fetched_at, raw_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(report_code) DO UPDATE SET
                    title = excluded.title,
                    source_url = excluded.source_url,
                    fetched_at = excluded.fetched_at,
                    raw_json = excluded.raw_json
                """,
                (
                    report_code,
                    title,
                    report_url,
                    fetched_at,
                    self._json({"report_code": report_code, "fights": fights}),
                ),
            )

            self.connection.execute(
                "DELETE FROM log_fight WHERE report_code = ?",
                (report_code,),
            )

            for fight in fights:
                self.connection.execute(
                    """
                    INSERT INTO log_fight (
                        report_code, fight_id, name, kill, difficulty,
                        boss_percentage, start_time, end_time, encounter_id,
                        raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report_code,
                        int(fight.get("id", -1)),
                        fight.get("name"),
                        int(bool(fight.get("kill"))) if fight.get("kill") is not None else None,
                        fight.get("difficulty"),
                        fight.get("bossPercentage"),
                        fight.get("startTime"),
                        fight.get("endTime"),
                        fight.get("encounterID"),
                        self._json(fight),
                    ),
                )

            self.connection.commit()
            self._manifest_finish(
                fights_manifest,
                status="imported",
                record_count=len(fights),
            )
        except Exception as exc:
            self.connection.rollback()
            self._manifest_finish(
                fights_manifest,
                status="failed",
                record_count=0,
                error_message=str(exc),
            )
            raise

        aura_total = 0
        for fight in fights:
            fight_id = int(fight.get("id", -1))
            start_time = float(fight.get("startTime", 0))
            end_time = float(fight.get("endTime", 0))
            if fight_id < 0 or end_time <= start_time:
                continue

            for data_type, hostility_type in (
                ("Buffs", "Friendlies"),
                ("Debuffs", "Enemies"),
            ):
                aura_total += self.import_aura_table(
                    report_code=report_code,
                    fight_id=fight_id,
                    start_time=start_time,
                    end_time=end_time,
                    data_type=data_type,
                    hostility_type=hostility_type,
                )

        return {"fights": len(fights), "auras": aura_total}

    def import_aura_table(
        self,
        *,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
        data_type: str,
        hostility_type: str,
        source_id: int | None = None,
    ) -> int:
        manifest_id = self._manifest_start(
            export_name=f"fight_{fight_id}_{data_type.lower()}_{hostility_type.lower()}",
            export_type="aura_table",
            report_code=report_code,
            request={
                "query": "AuraTable",
                "report_code": report_code,
                "fight_id": fight_id,
                "start_time": start_time,
                "end_time": end_time,
                "data_type": data_type,
                "hostility_type": hostility_type,
                "source_id": source_id,
            },
            destination_tables=["log_aura"],
        )

        try:
            auras = self.client.get_aura_table(
                report_code=report_code,
                fight_id=fight_id,
                start_time=start_time,
                end_time=end_time,
                data_type=data_type,
                hostility_type=hostility_type,
                source_id=source_id,
            )

            normalized_source_id = -1 if source_id is None else int(source_id)
            self.connection.execute(
                """
                DELETE FROM log_aura
                WHERE report_code = ?
                  AND fight_id = ?
                  AND data_type = ?
                  AND hostility_type = ?
                  AND source_id = ?
                """,
                (
                    report_code,
                    fight_id,
                    data_type,
                    hostility_type,
                    normalized_source_id,
                ),
            )

            for aura in auras:
                self.connection.execute(
                    """
                    INSERT OR REPLACE INTO log_aura (
                        report_code, fight_id, data_type, hostility_type,
                        source_id, aura_name, aura_guid, total_uptime,
                        total_uses, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report_code,
                        fight_id,
                        data_type,
                        hostility_type,
                        normalized_source_id,
                        aura.get("name"),
                        aura.get("guid"),
                        aura.get("totalUptime"),
                        aura.get("totalUses"),
                        self._json(aura),
                    ),
                )

            self.connection.commit()
            self._manifest_finish(
                manifest_id,
                status="imported",
                record_count=len(auras),
            )
            return len(auras)
        except Exception as exc:
            self.connection.rollback()
            self._manifest_finish(
                manifest_id,
                status="failed",
                record_count=0,
                error_message=str(exc),
            )
            raise
