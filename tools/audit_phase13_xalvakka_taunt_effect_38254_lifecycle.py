from __future__ import annotations

"""Drill into candidate taunt-state effect ability 38254 on Xalvakka adds.

This research audit intentionally treats ability 38254 as a *candidate* lifecycle state.
It resolves any canonical game-database identity available for the effect, then pairs
apply/remove events per report/fight/source/target/target-instance. Re-applications close
an existing interval at the re-application timestamp and begin a new interval so refresh
shape remains visible rather than being silently merged.

The audit does not promote 38254 to canonical taunt ownership. Promotion requires the
observed lifecycle shape to be compatible with taunt duration semantics and sufficiently
complete across the reviewed add sample.
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import statistics

ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_RESEARCH_DB = ROOT / "research" / "xalvakka_esologs_runtime.db"
_DEFAULT_GAME_DB = ROOT / "data" / "eso.db"
_EFFECT_ID = 38254
_TARGET_NAMES = ("Iron Atronach", "Daedroth")
_APPLY_TYPES = {"applydebuff", "applydebuffstack", "refreshdebuff"}
_REMOVE_TYPES = {"removedebuff", "removedebuffstack"}


@dataclass(frozen=True)
class EffectInterval:
    report_code: str
    fight_id: int
    actor_name: str
    target_instance: int
    source_id: int | None
    start_ms: float
    end_ms: float | None
    close_reason: str

    @property
    def duration_ms(self) -> float | None:
        if self.end_ms is None:
            return None
        return max(0.0, self.end_ms - self.start_ms)


def _open_read_only(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def _ability_identity(game_db: Path) -> tuple[str, str]:
    db = _open_read_only(game_db)
    try:
        columns = {
            str(row[1])
            for row in db.execute("PRAGMA table_info(ability)").fetchall()
        }
        selected = ["ability_id"]
        for name in ("name", "raw_description", "description", "coef_description"):
            if name in columns:
                selected.append(name)
        row = db.execute(
            f"SELECT {', '.join(selected)} FROM ability WHERE ability_id=? LIMIT 1",
            (_EFFECT_ID,),
        ).fetchone()
        if row is None:
            return (f"ability-{_EFFECT_ID}", "")
        name = str(row["name"] or f"ability-{_EFFECT_ID}").strip() if "name" in row.keys() else f"ability-{_EFFECT_ID}"
        descriptions = []
        for key in ("raw_description", "description", "coef_description"):
            if key in row.keys() and row[key]:
                text = " ".join(str(row[key]).split())
                if text and text not in descriptions:
                    descriptions.append(text)
        return name, " | ".join(descriptions)
    finally:
        db.close()


def observe(research_db: Path) -> tuple[EffectInterval, ...]:
    db = _open_read_only(research_db)
    try:
        actors = db.execute(
            """
            SELECT report_code, actor_id, name
            FROM log_report_actor
            WHERE name IN (?, ?)
            """,
            _TARGET_NAMES,
        ).fetchall()
        actor_map = {
            (str(row["report_code"]), int(row["actor_id"])): str(row["name"])
            for row in actors
        }
        rows = db.execute(
            """
            SELECT e.report_code, e.fight_id, e.timestamp, lower(e.event_type) AS event_type,
                   e.source_id, e.target_id,
                   COALESCE(e.target_instance,
                            CAST(json_extract(e.raw_json, '$.targetInstance') AS INTEGER), 0) AS target_instance
            FROM log_event e
            JOIN log_fight f
              ON f.report_code=e.report_code AND f.fight_id=e.fight_id
            WHERE lower(trim(f.name))='xalvakka'
              AND e.ability_game_id=?
              AND lower(e.event_type) IN ('applydebuff','applydebuffstack','refreshdebuff','removedebuff','removedebuffstack')
            ORDER BY e.report_code, e.fight_id, e.timestamp, e.event_index
            """,
            (_EFFECT_ID,),
        ).fetchall()

        open_by_key: dict[tuple[str, int, int | None, int, int], tuple[float, str]] = {}
        intervals: list[EffectInterval] = []
        for row in rows:
            report = str(row["report_code"])
            target_id = int(row["target_id"] or 0)
            actor_name = actor_map.get((report, target_id))
            if actor_name is None:
                continue
            fight_id = int(row["fight_id"])
            source_id = None if row["source_id"] is None else int(row["source_id"])
            instance = int(row["target_instance"] or 0)
            event_type = str(row["event_type"])
            timestamp = float(row["timestamp"])
            key = (report, fight_id, source_id, target_id, instance)

            if event_type in _APPLY_TYPES:
                prior = open_by_key.pop(key, None)
                if prior is not None:
                    intervals.append(
                        EffectInterval(report, fight_id, actor_name, instance, source_id, prior[0], timestamp, "reapply")
                    )
                open_by_key[key] = (timestamp, event_type)
            elif event_type in _REMOVE_TYPES:
                prior = open_by_key.pop(key, None)
                if prior is not None:
                    intervals.append(
                        EffectInterval(report, fight_id, actor_name, instance, source_id, prior[0], timestamp, "remove")
                    )

        for (report, fight_id, source_id, target_id, instance), (start, _event_type) in open_by_key.items():
            actor_name = actor_map.get((report, target_id))
            if actor_name is not None:
                intervals.append(
                    EffectInterval(report, fight_id, actor_name, instance, source_id, start, None, "open")
                )
        return tuple(intervals)
    finally:
        db.close()


def _summary(values_ms: tuple[float, ...]) -> str:
    if not values_ms:
        return "samples=0"
    seconds = tuple(value / 1000.0 for value in values_ms)
    return (
        f"samples={len(seconds)} median={statistics.median(seconds):.3f}s "
        f"min={min(seconds):.3f}s max={max(seconds):.3f}s"
    )


def audit(research_db: Path, game_db: Path) -> tuple[str, ...]:
    name, description = _ability_identity(game_db)
    intervals = observe(research_db)
    lines = [
        "PHASE 13 XALVAKKA TAUNT EFFECT 38254 LIFECYCLE AUDIT",
        f"RESEARCH_DATABASE: {research_db}",
        f"GAME_DATABASE: {game_db}",
        f"EFFECT_ID={_EFFECT_ID}",
        f"GAME_IDENTITY={name}",
        f"GAME_DESCRIPTION={description or 'unresolved'}",
        f"INTERVALS={len(intervals)}",
    ]

    for actor_name in _TARGET_NAMES:
        actor_rows = tuple(row for row in intervals if row.actor_name == actor_name)
        closed = tuple(row.duration_ms for row in actor_rows if row.duration_ms is not None)
        removed = sum(row.close_reason == "remove" for row in actor_rows)
        reapplied = sum(row.close_reason == "reapply" for row in actor_rows)
        opened = sum(row.close_reason == "open" for row in actor_rows)
        instances = len({(row.report_code, row.fight_id, row.target_instance) for row in actor_rows})
        lines.append(
            f"ACTOR_SUMMARY: actor={actor_name} instances={instances} intervals={len(actor_rows)} "
            f"remove_closed={removed} reapply_closed={reapplied} still_open={opened}"
        )
        lines.append(f"DURATION: actor={actor_name} {_summary(tuple(float(v) for v in closed))}")

    for row in intervals:
        duration = "open" if row.duration_ms is None else f"{row.duration_ms / 1000.0:.3f}s"
        lines.append(
            "LIFECYCLE_INTERVAL: "
            f"report={row.report_code} fight_id={row.fight_id} actor={row.actor_name} "
            f"instance={row.target_instance} source_id={row.source_id} "
            f"duration={duration} close={row.close_reason}"
        )

    lines.append(
        "INTERPRETATION=ability 38254 remains a taunt-state candidate; duration/lifecycle shape may support ownership only after identity and completeness review"
    )
    return tuple(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_RESEARCH_DB)
    parser.add_argument("--game-db", type=Path, default=_DEFAULT_GAME_DB)
    args = parser.parse_args()
    for path in (args.db, args.game_db):
        if not path.exists():
            print(f"AUDIT ERROR: database does not exist: {path}")
            return 2
    try:
        for line in audit(args.db, args.game_db):
            print(line)
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
