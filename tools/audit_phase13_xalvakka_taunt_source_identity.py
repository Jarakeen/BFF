from __future__ import annotations

"""Audit player identities behind Xalvakka add taunt-state sources.

This is observational evidence only. It resolves report actor identity for every friendly
source that owns reviewed taunt-state effect 38254 on Iron Atronach or Daedroth targets,
then summarizes which add instances each source touched. It does not infer Main/Off Tank
from class, build, roster order, or player name.
"""

import argparse
from collections import defaultdict
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DB = ROOT / "research" / "xalvakka_esologs_runtime.db"
_TAUNT_EFFECT_ID = 38254
_TARGET_NAMES = ("Iron Atronach", "Daedroth")


def _open_read_only(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def audit(db_path: Path) -> tuple[str, ...]:
    db = _open_read_only(db_path)
    try:
        actor_columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_report_actor)").fetchall()}
        selected = ["report_code", "actor_id", "name"]
        for column in ("type", "sub_type", "game_id"):
            if column in actor_columns:
                selected.append(column)
        actors = db.execute(
            f"SELECT {', '.join(selected)} FROM log_report_actor"
        ).fetchall()
        actor_by_key = {
            (str(row["report_code"]), int(row["actor_id"])): row
            for row in actors
        }

        target_rows = db.execute(
            "SELECT report_code, actor_id, name FROM log_report_actor WHERE name IN (?, ?)",
            _TARGET_NAMES,
        ).fetchall()
        target_name = {
            (str(row["report_code"]), int(row["actor_id"])): str(row["name"])
            for row in target_rows
        }

        rows = db.execute(
            """
            SELECT e.report_code, e.fight_id, e.source_id, e.target_id,
                   COALESCE(e.target_instance,
                            CAST(json_extract(e.raw_json, '$.targetInstance') AS INTEGER), 0) AS target_instance,
                   lower(e.event_type) AS event_type
            FROM log_event e
            JOIN log_fight f
              ON f.report_code=e.report_code AND f.fight_id=e.fight_id
            WHERE lower(trim(f.name))='xalvakka'
              AND e.ability_game_id=?
              AND e.source_is_friendly=1
              AND lower(e.event_type) IN ('applydebuff','refreshdebuff','removedebuff')
            ORDER BY e.report_code, e.fight_id, e.timestamp, e.event_index
            """,
            (_TAUNT_EFFECT_ID,),
        ).fetchall()
    finally:
        db.close()

    source_instances: dict[tuple[str, int], set[tuple[int, str, int]]] = defaultdict(set)
    source_events: dict[tuple[str, int], int] = defaultdict(int)
    source_actor_mix: dict[tuple[str, int], dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in rows:
        report = str(row["report_code"])
        source_id = int(row["source_id"] or 0)
        target_id = int(row["target_id"] or 0)
        actor = target_name.get((report, target_id))
        if not source_id or actor is None:
            continue
        key = (report, source_id)
        source_events[key] += 1
        source_actor_mix[key][actor] += 1
        source_instances[key].add(
            (int(row["fight_id"]), actor, int(row["target_instance"] or 0))
        )

    lines = [
        "PHASE 13 XALVAKKA TAUNT SOURCE IDENTITY AUDIT",
        f"DATABASE: {db_path}",
        f"TAUNT_STATE_EFFECT_ID={_TAUNT_EFFECT_ID}",
        f"OBSERVED_SOURCES={len(source_instances)}",
    ]

    for key in sorted(source_instances):
        report, source_id = key
        actor_row = actor_by_key.get(key)
        name = str(actor_row["name"] or f"actor-{source_id}") if actor_row is not None else f"actor-{source_id}"
        extras = []
        if actor_row is not None:
            for column in ("type", "sub_type", "game_id"):
                if column in actor_row.keys() and actor_row[column] not in (None, ""):
                    extras.append(f"{column}={actor_row[column]}")
        mix = ",".join(
            f"{actor}={count}"
            for actor, count in sorted(source_actor_mix[key].items())
        )
        instances = sorted(source_instances[key])
        lines.append(
            f"SOURCE: report={report} source_id={source_id} name={name} "
            f"events={source_events[key]} instances={len(instances)} actor_events=[{mix}] "
            + (" ".join(extras) if extras else "identity_metadata=limited")
        )
        for fight_id, actor, instance in instances:
            lines.append(
                f"  INSTANCE: fight_id={fight_id} actor={actor} instance={instance}"
            )

    lines.append(
        "INTERPRETATION=source identity is observational only; Main/Off Tank role assignment requires independent reviewed roster/prescription evidence"
    )
    return tuple(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_DB)
    args = parser.parse_args()
    if not args.db.exists():
        print(f"AUDIT ERROR: database does not exist: {args.db}")
        return 2
    try:
        for line in audit(args.db):
            print(line)
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
