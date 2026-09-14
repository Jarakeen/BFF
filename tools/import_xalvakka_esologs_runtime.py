from __future__ import annotations

"""Import only Xalvakka fights from one ESO Logs report into a dedicated runtime DB."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.esologs_client import EsoLogsClient
from services.esologs_combat_importer import EsoLogsCombatImporter
from services.esologs_importer import EsoLogsImporter
from services.settings_service import SettingsService
from tools.audit_phase13_xalvakka_transition_resume_runtime import audit

_DEFAULT_DATABASE = ROOT / "research" / "xalvakka_esologs_runtime.db"


def select_xalvakka_fights(fights: list[dict]) -> tuple[dict, ...]:
    return tuple(
        fight
        for fight in fights
        if str(fight.get("name") or "").strip().casefold() == "xalvakka"
        and int(fight.get("id", -1)) >= 0
    )


def persist_report_metadata(
    connection: sqlite3.Connection,
    *,
    report_code: str,
    fights: tuple[dict, ...],
) -> None:
    # Reuse the canonical ESO Logs persistence schema without importing unrelated
    # fights or aura tables. Combat events are imported separately below.
    EsoLogsImporter(connection, client=None)  # type: ignore[arg-type]
    fetched_at = datetime.now(timezone.utc).isoformat()
    source_url = f"https://www.esologs.com/reports/{report_code}"
    connection.execute(
        """
        INSERT INTO log_report(report_code, title, source_url, fetched_at, raw_json)
        VALUES (?, NULL, ?, ?, ?)
        ON CONFLICT(report_code) DO UPDATE SET
            source_url=excluded.source_url,
            fetched_at=excluded.fetched_at,
            raw_json=excluded.raw_json
        """,
        (
            report_code,
            source_url,
            fetched_at,
            json.dumps({"report_code": report_code, "selected_fights": fights}, sort_keys=True),
        ),
    )
    for fight in fights:
        connection.execute(
            """
            INSERT INTO log_fight(
                report_code, fight_id, name, kill, difficulty, boss_percentage,
                start_time, end_time, encounter_id, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(report_code, fight_id) DO UPDATE SET
                name=excluded.name,
                kill=excluded.kill,
                difficulty=excluded.difficulty,
                boss_percentage=excluded.boss_percentage,
                start_time=excluded.start_time,
                end_time=excluded.end_time,
                encounter_id=excluded.encounter_id,
                raw_json=excluded.raw_json
            """,
            (
                report_code,
                int(fight["id"]),
                fight.get("name"),
                None if fight.get("kill") is None else int(bool(fight.get("kill"))),
                fight.get("difficulty"),
                fight.get("bossPercentage"),
                fight.get("startTime"),
                fight.get("endTime"),
                fight.get("encounterID"),
                json.dumps(fight, sort_keys=True),
            ),
        )
    connection.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_code", help="ESO Logs report code or report URL")
    parser.add_argument(
        "--db",
        type=Path,
        default=_DEFAULT_DATABASE,
        help=f"Dedicated runtime database (default: {_DEFAULT_DATABASE})",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=Path("settings.json"),
        help="BFF settings path; ESO Logs secret is loaded from the OS keyring.",
    )
    parser.add_argument("--gap-ms", type=float, default=3000.0)
    args = parser.parse_args()

    settings = SettingsService(args.settings).load()
    client = EsoLogsClient(
        client_id=settings.get("EsoLogsClientId", ""),
        client_secret=settings.get("EsoLogsClientSecret", ""),
    )
    code = client.normalize_report_code(args.report_code)
    if not code:
        print("IMPORT ERROR: ESO Logs report code is empty")
        return 2

    try:
        fights = client.get_fights(code)
        selected = select_xalvakka_fights(fights)
        if not selected:
            print(f"IMPORT ERROR: report {code} contains no fight named Xalvakka")
            return 2

        args.db.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(args.db)
        try:
            persist_report_metadata(connection, report_code=code, fights=selected)
            result = EsoLogsCombatImporter(connection, client).import_report(
                code,
                fight_ids=[int(fight["id"]) for fight in selected],
                gap_threshold_ms=args.gap_ms,
            )
        finally:
            connection.close()

        print("XALVAKKA ESO LOGS IMPORT")
        print(f"REPORT: {code}")
        print(f"DATABASE: {args.db}")
        print("FIGHTS: " + ", ".join(str(int(fight["id"])) for fight in selected))
        print(
            f"IMPORTED: fights={result['fights']} actors={result['actors']} "
            f"events={result['events']} observed_windows={result['observed_windows']}"
        )
        for line in audit(args.db, minimum_gap_ms=args.gap_ms):
            print(line)
        return 0
    except Exception as exc:
        print(f"IMPORT ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
