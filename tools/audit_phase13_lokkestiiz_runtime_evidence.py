from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir


def _open_read_only(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _relative_seconds(timestamp: object, start_time: object) -> float | None:
    if not isinstance(timestamp, (int, float)) or not isinstance(start_time, (int, float)):
        return None
    return (float(timestamp) - float(start_time)) / 1000.0


def _format_seconds(value: float | None) -> str:
    return "?" if value is None else f"{value:.3f}s"


def _fight_rows(connection: sqlite3.Connection) -> tuple[sqlite3.Row, ...]:
    rows = connection.execute(
        """
        SELECT report_code, fight_id, name, kill, difficulty, boss_percentage,
               start_time, end_time, encounter_id
        FROM log_fight
        WHERE lower(name) LIKE '%lokkestiiz%'
        ORDER BY report_code, fight_id
        """
    ).fetchall()
    return tuple(rows)


def _healer_rows(
    connection: sqlite3.Connection,
    *,
    report_code: str,
    fight_id: int,
) -> tuple[sqlite3.Row, ...]:
    rows = connection.execute(
        """
        SELECT actor_id, name, display_name, role, actor_type
        FROM log_actor
        WHERE report_code=? AND fight_id=? AND lower(coalesce(role, ''))='healer'
        ORDER BY actor_id
        """,
        (report_code, fight_id),
    ).fetchall()
    return tuple(rows)


def _three_occurrence_hostile_signatures(
    connection: sqlite3.Connection,
    *,
    report_code: str,
    fight_id: int,
    start_time: float | int | None,
) -> tuple[str, ...]:
    rows = connection.execute(
        """
        SELECT ability_game_id, event_type, COUNT(*) AS event_count,
               MIN(timestamp) AS first_timestamp,
               MAX(timestamp) AS last_timestamp
        FROM log_event
        WHERE report_code=? AND fight_id=?
          AND source_is_friendly=0
          AND ability_game_id IS NOT NULL
          AND lower(event_type) IN ('begincast', 'cast', 'damage', 'applydebuff', 'applybuff')
        GROUP BY ability_game_id, event_type
        HAVING COUNT(*)=3
        ORDER BY event_type, ability_game_id
        """,
        (report_code, fight_id),
    ).fetchall()
    lines: list[str] = []
    for row in rows:
        first = _relative_seconds(row["first_timestamp"], start_time)
        last = _relative_seconds(row["last_timestamp"], start_time)
        lines.append(
            "HOSTILE_SIGNATURE_X3: "
            f"ability_id={row['ability_game_id']} event_type={row['event_type']} "
            f"first={_format_seconds(first)} last={_format_seconds(last)}"
        )
    return tuple(lines)


def _resource_change_summary(
    connection: sqlite3.Connection,
    *,
    report_code: str,
    fight_id: int,
    actor_id: int,
    start_time: float | int | None,
) -> tuple[str, ...]:
    rows = connection.execute(
        """
        SELECT timestamp, event_type, ability_game_id, resource_change,
               resource_change_type, other_resource_change, max_resource_amount,
               raw_json
        FROM log_event
        WHERE report_code=? AND fight_id=? AND source_id=?
          AND (
                resource_change IS NOT NULL
             OR resource_change_type IS NOT NULL
             OR other_resource_change IS NOT NULL
             OR max_resource_amount IS NOT NULL
          )
        ORDER BY timestamp, event_index
        LIMIT 20
        """,
        (report_code, fight_id, actor_id),
    ).fetchall()
    if not rows:
        return (f"HEALER_RESOURCE_EVENTS: actor_id={actor_id} none",)

    lines: list[str] = []
    types = sorted(
        {
            str(row["resource_change_type"])
            for row in rows
            if row["resource_change_type"] is not None
        }
    )
    lines.append(
        f"HEALER_RESOURCE_TYPES: actor_id={actor_id} "
        + (", ".join(types) if types else "none in first 20 samples")
    )
    for row in rows[:10]:
        relative = _relative_seconds(row["timestamp"], start_time)
        raw_type = None
        try:
            raw = json.loads(row["raw_json"] or "{}")
            raw_type = raw.get("resourceChangeType")
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        lines.append(
            "HEALER_RESOURCE_SAMPLE: "
            f"actor_id={actor_id} t={_format_seconds(relative)} "
            f"event_type={row['event_type']} ability_id={row['ability_game_id']} "
            f"change={row['resource_change']} type={row['resource_change_type']} "
            f"other={row['other_resource_change']} max={row['max_resource_amount']} "
            f"raw_type={raw_type}"
        )
    return tuple(lines)


def audit(*, database_path: Path) -> tuple[str, ...]:
    connection = _open_read_only(database_path)
    try:
        required = ("log_fight", "log_actor", "log_event")
        missing = tuple(name for name in required if not _table_exists(connection, name))
        if missing:
            raise ValueError("ESO Logs runtime tables are missing: " + ", ".join(missing))

        fights = _fight_rows(connection)
        lines: list[str] = ["PHASE 13 LOKKESTIIZ RUNTIME EVIDENCE AUDIT"]
        lines.append(f"DATABASE: {database_path}")
        lines.append(f"LOKKESTIIZ_FIGHTS: {len(fights)}")
        if not fights:
            lines.append("RUNTIME_EVIDENCE_READY: false")
            lines.append("UNRESOLVED: no imported Lokkestiiz fights exist in log_fight")
            return tuple(lines)

        for fight in fights:
            report_code = str(fight["report_code"])
            fight_id = int(fight["fight_id"])
            start_time = fight["start_time"]
            end_time = fight["end_time"]
            duration = _relative_seconds(end_time, start_time)
            lines.append(
                "FIGHT: "
                f"report={report_code} fight_id={fight_id} name={fight['name']} "
                f"kill={fight['kill']} difficulty={fight['difficulty']} "
                f"encounter_id={fight['encounter_id']} duration={_format_seconds(duration)}"
            )

            healers = _healer_rows(
                connection,
                report_code=report_code,
                fight_id=fight_id,
            )
            if not healers:
                lines.append("HEALERS: none")
            for healer in healers:
                lines.append(
                    "HEALER: "
                    f"actor_id={healer['actor_id']} name={healer['name']} "
                    f"display_name={healer['display_name']} role={healer['role']}"
                )
                lines.extend(
                    _resource_change_summary(
                        connection,
                        report_code=report_code,
                        fight_id=fight_id,
                        actor_id=int(healer["actor_id"]),
                        start_time=start_time,
                    )
                )

            signatures = _three_occurrence_hostile_signatures(
                connection,
                report_code=report_code,
                fight_id=fight_id,
                start_time=start_time,
            )
            if signatures:
                lines.extend(signatures)
            else:
                lines.append("HOSTILE_SIGNATURE_X3: none")

        lines.append("RUNTIME_EVIDENCE_READY: false")
        lines.append(
            "UNRESOLVED: a reviewed hostile event signature must be identified as the "
            "Lokkestiiz landing boundary before log timestamps may become landing clocks"
        )
        lines.append(
            "UNRESOLVED: starting Ultimate may be derived only if the imported resource "
            "event stream proves an Ultimate resource identity and amount at pull start"
        )
        return tuple(lines)
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect imported ESO Logs evidence for Lokkestiiz landing and starting-Ultimate markers."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=get_data_dir() / "eso.db",
    )
    args = parser.parse_args()
    try:
        lines = audit(database_path=args.database)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
