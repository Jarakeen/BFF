from __future__ import annotations

"""Audit earliest raw ESO Logs signals for named Xalvakka add instances.

This research tool looks for a stronger activity boundary than first friendly damage.
For each Iron Atronach/Daedroth instance it compares:
- earliest event of any kind involving the NPC instance,
- earliest event sourced by the NPC instance,
- earliest hostile cast sourced by the NPC instance,
- first friendly damage to that NPC instance.

All timestamps remain observational. None is promoted as exact spawn or taunt-required
timing by this audit.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DEFAULT_DATABASE = ROOT / "research" / "xalvakka_esologs_runtime.db"
_TARGET_NAMES = ("Iron Atronach", "Daedroth")
_CAST_TYPES = {"cast", "begincast"}


@dataclass(frozen=True)
class AddSignalObservation:
    report_code: str
    fight_id: int
    actor_name: str
    actor_id: int
    instance_id: int
    fight_start_ms: float
    first_involving_ms: float | None
    first_source_ms: float | None
    first_cast_ms: float | None
    first_friendly_damage_ms: float | None

    @staticmethod
    def _delta(left: float | None, right: float | None) -> float | None:
        if left is None or right is None:
            return None
        return right - left

    @property
    def involving_to_damage_ms(self) -> float | None:
        return self._delta(self.first_involving_ms, self.first_friendly_damage_ms)

    @property
    def source_to_damage_ms(self) -> float | None:
        return self._delta(self.first_source_ms, self.first_friendly_damage_ms)

    @property
    def cast_to_damage_ms(self) -> float | None:
        return self._delta(self.first_cast_ms, self.first_friendly_damage_ms)


def _open_read_only(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def _instance_expr(prefix: str) -> str:
    # ESO Logs commonly carries sourceInstance only in raw JSON. target_instance is
    # already projected into a column by the importer. Instance zero remains valid.
    if prefix == "source":
        return "COALESCE(CAST(json_extract(raw_json, '$.sourceInstance') AS INTEGER), 0)"
    return "COALESCE(target_instance, CAST(json_extract(raw_json, '$.targetInstance') AS INTEGER), 0)"


def observe(database: Path) -> tuple[AddSignalObservation, ...]:
    db = _open_read_only(database)
    try:
        actors = tuple(
            db.execute(
                """
                SELECT report_code, actor_id, name
                FROM log_report_actor
                WHERE name IN (?, ?)
                ORDER BY report_code, name, actor_id
                """,
                _TARGET_NAMES,
            ).fetchall()
        )
        actor_map: dict[tuple[str, int], str] = {
            (str(row["report_code"]), int(row["actor_id"])): str(row["name"])
            for row in actors
        }
        observations: list[AddSignalObservation] = []

        fights = tuple(
            db.execute(
                """
                SELECT report_code, fight_id, start_time
                FROM log_fight
                WHERE lower(trim(name))='xalvakka'
                ORDER BY report_code, fight_id
                """
            ).fetchall()
        )
        for fight in fights:
            report_code = str(fight["report_code"])
            fight_id = int(fight["fight_id"])
            fight_start = float(fight["start_time"] or 0.0)
            actor_ids = tuple(
                actor_id
                for (report, actor_id), _name in actor_map.items()
                if report == report_code
            )
            if not actor_ids:
                continue

            placeholders = ",".join("?" for _ in actor_ids)
            instance_rows = db.execute(
                f"""
                SELECT actor_id, instance_id, MIN(timestamp) AS first_friendly_damage
                FROM (
                    SELECT target_id AS actor_id,
                           {_instance_expr('target')} AS instance_id,
                           timestamp
                    FROM log_event
                    WHERE report_code=? AND fight_id=?
                      AND event_type='damage'
                      AND source_is_friendly=1
                      AND target_is_friendly=0
                      AND target_id IN ({placeholders})
                )
                GROUP BY actor_id, instance_id
                ORDER BY first_friendly_damage
                """,
                (report_code, fight_id, *actor_ids),
            ).fetchall()

            for instance in instance_rows:
                actor_id = int(instance["actor_id"])
                instance_id = int(instance["instance_id"] or 0)
                first_damage = float(instance["first_friendly_damage"])

                involving = db.execute(
                    f"""
                    SELECT MIN(timestamp)
                    FROM log_event
                    WHERE report_code=? AND fight_id=? AND (
                        (source_id=? AND {_instance_expr('source')}=?) OR
                        (target_id=? AND {_instance_expr('target')}=?)
                    )
                    """,
                    (report_code, fight_id, actor_id, instance_id, actor_id, instance_id),
                ).fetchone()[0]

                source = db.execute(
                    f"""
                    SELECT MIN(timestamp)
                    FROM log_event
                    WHERE report_code=? AND fight_id=?
                      AND source_id=? AND {_instance_expr('source')}=?
                    """,
                    (report_code, fight_id, actor_id, instance_id),
                ).fetchone()[0]

                cast_placeholders = ",".join("?" for _ in _CAST_TYPES)
                cast = db.execute(
                    f"""
                    SELECT MIN(timestamp)
                    FROM log_event
                    WHERE report_code=? AND fight_id=?
                      AND source_id=? AND {_instance_expr('source')}=?
                      AND lower(event_type) IN ({cast_placeholders})
                    """,
                    (report_code, fight_id, actor_id, instance_id, *sorted(_CAST_TYPES)),
                ).fetchone()[0]

                observations.append(
                    AddSignalObservation(
                        report_code=report_code,
                        fight_id=fight_id,
                        actor_name=actor_map[(report_code, actor_id)],
                        actor_id=actor_id,
                        instance_id=instance_id,
                        fight_start_ms=fight_start,
                        first_involving_ms=None if involving is None else float(involving),
                        first_source_ms=None if source is None else float(source),
                        first_cast_ms=None if cast is None else float(cast),
                        first_friendly_damage_ms=first_damage,
                    )
                )
        return tuple(observations)
    finally:
        db.close()


def _fmt_absolute(value: float | None, fight_start: float) -> str:
    if value is None:
        return "none"
    return f"{(value - fight_start) / 1000.0:.3f}s"


def _fmt_lag(value: float | None) -> str:
    if value is None:
        return "none"
    return f"{value / 1000.0:.3f}s"


def audit(database: Path) -> tuple[str, ...]:
    rows = observe(database)
    lines = [
        "PHASE 13 XALVAKKA ADD EARLIEST EVENT SIGNAL AUDIT",
        f"DATABASE: {database}",
        f"OBSERVATIONS: {len(rows)}",
    ]
    for row in rows:
        lines.append(
            "ADD_SIGNAL: "
            f"report={row.report_code} fight_id={row.fight_id} actor={row.actor_name} "
            f"instance={row.instance_id} "
            f"first_involving={_fmt_absolute(row.first_involving_ms, row.fight_start_ms)} "
            f"first_source={_fmt_absolute(row.first_source_ms, row.fight_start_ms)} "
            f"first_cast={_fmt_absolute(row.first_cast_ms, row.fight_start_ms)} "
            f"first_friendly_damage={_fmt_absolute(row.first_friendly_damage_ms, row.fight_start_ms)} "
            f"involving_to_damage={_fmt_lag(row.involving_to_damage_ms)} "
            f"source_to_damage={_fmt_lag(row.source_to_damage_ms)} "
            f"cast_to_damage={_fmt_lag(row.cast_to_damage_ms)}"
        )

    for actor_name in _TARGET_NAMES:
        actor_rows = tuple(row for row in rows if row.actor_name == actor_name)
        lines.append(
            f"SIGNAL_COVERAGE: actor={actor_name} instances={len(actor_rows)} "
            f"involving={sum(row.first_involving_ms is not None for row in actor_rows)} "
            f"source={sum(row.first_source_ms is not None for row in actor_rows)} "
            f"cast={sum(row.first_cast_ms is not None for row in actor_rows)}"
        )
    lines.append(
        "INTERPRETATION=earliest raw event signals are observational activity evidence; review repeatability before promoting add taunt-entry timing"
    )
    return tuple(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_DATABASE)
    args = parser.parse_args()
    if not args.db.exists():
        print(f"AUDIT ERROR: database does not exist: {args.db}")
        return 2
    try:
        lines = audit(args.db)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
