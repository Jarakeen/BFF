from __future__ import annotations

"""Read-only ESO Logs audit for Xalvakka retreat/resume timing.

The audit does not promote strategy policy. It correlates observed Xalvakka health
threshold crossings with the first substantial friendly-damage gap that follows and
the first friendly damage event when Xalvakka becomes damageable again. Repeated
fights remain separate candidate evidence until reviewed.
"""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from tools.discover_esologs_runtime_db import discover


_THRESHOLDS = (0.70, 0.40)


@dataclass(frozen=True)
class XalvakkaTransitionObservation:
    report_code: str
    fight_id: int
    threshold_fraction: float
    crossing_time_ms: float
    gap_start_time_ms: float
    resume_time_ms: float
    gap_ms: float
    crossing_hp_fraction: float | None
    resume_hp_fraction: float | None

    @property
    def transition_delay_ms(self) -> float:
        return self.resume_time_ms - self.crossing_time_ms


def _open_read_only(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(path)
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def _default_roots() -> tuple[Path, ...]:
    return (get_data_dir(), ROOT / "data", ROOT / "user_data", ROOT / "research")


def _xalvakka_fight_count(path: Path) -> int:
    """Return imported Xalvakka fight count for a schema-compatible runtime DB.

    Database discovery is intentionally content-aware here. A backup/test database can
    contain the ESO Logs tables while containing no Xalvakka evidence at all; selecting
    such a file merely because its schema matches produces a misleading zero-observation
    audit.
    """
    try:
        db = _open_read_only(path)
    except (OSError, sqlite3.Error):
        return 0
    try:
        row = db.execute(
            "SELECT COUNT(*) FROM log_fight WHERE lower(name) LIKE '%xalvakka%'"
        ).fetchone()
        return 0 if row is None else int(row[0] or 0)
    except sqlite3.Error:
        return 0
    finally:
        db.close()


def _resolve_database(
    path: Path | None,
    *,
    roots: tuple[Path, ...] | None = None,
) -> Path:
    if path is not None:
        return path

    matches = discover(roots=roots or _default_roots())
    if not matches:
        raise ValueError("no ESO Logs runtime database was found")

    candidates = tuple(
        (item, _xalvakka_fight_count(item))
        for item in matches
    )
    xalvakka_candidates = tuple(
        (item, count) for item, count in candidates if count > 0
    )
    if not xalvakka_candidates:
        details = ", ".join(
            f"{item} (xalvakka_fights={count})" for item, count in candidates
        )
        raise ValueError(
            "ESO Logs runtime database(s) were found, but none contains an imported "
            "Xalvakka fight; import Xalvakka ESO Logs evidence or pass --database "
            f"explicitly. Discovered: {details}"
        )
    if len(xalvakka_candidates) > 1:
        choices = ", ".join(
            f"{item} (xalvakka_fights={count})"
            for item, count in xalvakka_candidates
        )
        raise ValueError(
            "multiple ESO Logs runtime databases contain Xalvakka fights; pass "
            f"--database explicitly: {choices}"
        )
    return xalvakka_candidates[0][0]


def _tables(db: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }


def _fight_rows(db: sqlite3.Connection) -> tuple[sqlite3.Row, ...]:
    return tuple(
        db.execute(
            """
            SELECT report_code, fight_id, name, kill, difficulty, boss_percentage,
                   start_time, end_time, encounter_id
            FROM log_fight
            WHERE lower(name) LIKE '%xalvakka%'
            ORDER BY report_code, fight_id
            """
        ).fetchall()
    )


def _resource_fraction(raw_json: str) -> float | None:
    try:
        raw = json.loads(raw_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return None
    resources = raw.get("targetResources") or {}
    hp = resources.get("hitPoints")
    maximum = resources.get("maxHitPoints")
    try:
        hp_value = float(hp)
        max_value = float(maximum)
    except (TypeError, ValueError):
        return None
    if max_value <= 0:
        return None
    return hp_value / max_value


def _boss_target_id(db: sqlite3.Connection, report_code: str, fight_id: int) -> int | None:
    row = db.execute(
        """
        SELECT target_id,
               MAX(COALESCE(json_extract(raw_json, '$.targetResources.maxHitPoints'), 0)) AS max_hp,
               COUNT(*) AS event_count
        FROM log_event
        WHERE report_code=? AND fight_id=?
          AND event_type='damage'
          AND source_is_friendly=1
          AND target_is_friendly=0
          AND target_id IS NOT NULL
        GROUP BY target_id
        ORDER BY max_hp DESC, event_count DESC, target_id
        LIMIT 1
        """,
        (report_code, fight_id),
    ).fetchone()
    return None if row is None else int(row["target_id"])


def _damage_rows(
    db: sqlite3.Connection,
    report_code: str,
    fight_id: int,
    target_id: int,
) -> tuple[sqlite3.Row, ...]:
    return tuple(
        db.execute(
            """
            SELECT event_index, timestamp, amount, raw_json
            FROM log_event
            WHERE report_code=? AND fight_id=?
              AND event_type='damage'
              AND source_is_friendly=1
              AND target_id=?
            ORDER BY timestamp, event_index
            """,
            (report_code, fight_id, target_id),
        ).fetchall()
    )


def _find_crossing(rows: tuple[sqlite3.Row, ...], threshold: float) -> int | None:
    previous_fraction: float | None = None
    for index, row in enumerate(rows):
        current_fraction = _resource_fraction(str(row["raw_json"] or ""))
        if current_fraction is None:
            continue
        if current_fraction <= threshold and (
            previous_fraction is None or previous_fraction > threshold
        ):
            return index
        previous_fraction = current_fraction
    return None


def _find_resume_gap(
    rows: tuple[sqlite3.Row, ...],
    crossing_index: int,
    *,
    minimum_gap_ms: float,
    maximum_gap_start_delay_ms: float,
) -> tuple[int, int] | None:
    crossing_time = float(rows[crossing_index]["timestamp"])
    for index in range(crossing_index, len(rows) - 1):
        left = float(rows[index]["timestamp"])
        right = float(rows[index + 1]["timestamp"])
        if left - crossing_time > maximum_gap_start_delay_ms:
            break
        if right - left >= minimum_gap_ms:
            return index, index + 1
    return None


def observe(
    database_path: Path,
    *,
    minimum_gap_ms: float = 3000.0,
    maximum_gap_start_delay_ms: float = 15000.0,
) -> tuple[XalvakkaTransitionObservation, ...]:
    db = _open_read_only(database_path)
    try:
        missing = {"log_fight", "log_event"} - _tables(db)
        if missing:
            raise ValueError("ESO Logs runtime tables are missing: " + ", ".join(sorted(missing)))

        observations: list[XalvakkaTransitionObservation] = []
        for fight in _fight_rows(db):
            report_code = str(fight["report_code"])
            fight_id = int(fight["fight_id"])
            target_id = _boss_target_id(db, report_code, fight_id)
            if target_id is None:
                continue
            rows = _damage_rows(db, report_code, fight_id, target_id)
            if not rows:
                continue

            for threshold in _THRESHOLDS:
                crossing_index = _find_crossing(rows, threshold)
                if crossing_index is None:
                    continue
                pair = _find_resume_gap(
                    rows,
                    crossing_index,
                    minimum_gap_ms=minimum_gap_ms,
                    maximum_gap_start_delay_ms=maximum_gap_start_delay_ms,
                )
                if pair is None:
                    continue
                gap_start_index, resume_index = pair
                crossing = rows[crossing_index]
                gap_start = rows[gap_start_index]
                resume = rows[resume_index]
                observations.append(
                    XalvakkaTransitionObservation(
                        report_code=report_code,
                        fight_id=fight_id,
                        threshold_fraction=threshold,
                        crossing_time_ms=float(crossing["timestamp"]),
                        gap_start_time_ms=float(gap_start["timestamp"]),
                        resume_time_ms=float(resume["timestamp"]),
                        gap_ms=float(resume["timestamp"]) - float(gap_start["timestamp"]),
                        crossing_hp_fraction=_resource_fraction(str(crossing["raw_json"] or "")),
                        resume_hp_fraction=_resource_fraction(str(resume["raw_json"] or "")),
                    )
                )
        return tuple(observations)
    finally:
        db.close()


def audit(
    database_path: Path,
    *,
    minimum_gap_ms: float = 3000.0,
    maximum_gap_start_delay_ms: float = 15000.0,
) -> tuple[str, ...]:
    observations = observe(
        database_path,
        minimum_gap_ms=minimum_gap_ms,
        maximum_gap_start_delay_ms=maximum_gap_start_delay_ms,
    )
    lines = [
        "PHASE 13 XALVAKKA TRANSITION RESUME RUNTIME AUDIT",
        f"DATABASE: {database_path}",
        f"XALVAKKA_FIGHTS: {_xalvakka_fight_count(database_path)}",
        f"MINIMUM_DAMAGE_GAP_MS: {minimum_gap_ms:g}",
        f"MAXIMUM_GAP_START_DELAY_MS: {maximum_gap_start_delay_ms:g}",
        f"OBSERVATIONS: {len(observations)}",
    ]
    for row in observations:
        crossing_hp = "unknown" if row.crossing_hp_fraction is None else f"{row.crossing_hp_fraction * 100:.3f}%"
        resume_hp = "unknown" if row.resume_hp_fraction is None else f"{row.resume_hp_fraction * 100:.3f}%"
        lines.append(
            "TRANSITION_CANDIDATE: "
            f"report={row.report_code} fight_id={row.fight_id} "
            f"threshold={row.threshold_fraction * 100:g}% "
            f"crossing={row.crossing_time_ms / 1000.0:.3f}s "
            f"gap_start={row.gap_start_time_ms / 1000.0:.3f}s "
            f"resume={row.resume_time_ms / 1000.0:.3f}s "
            f"gap={row.gap_ms / 1000.0:.3f}s "
            f"crossing_hp={crossing_hp} resume_hp={resume_hp} "
            f"threshold_to_resume={row.transition_delay_ms / 1000.0:.3f}s"
        )
    if not observations:
        lines.append(
            "UNRESOLVED: imported Xalvakka fights were found, but no threshold-crossing plus substantial post-threshold Xalvakka damage gap was observed"
        )
    else:
        lines.append(
            "REVIEW_REQUIRED: compare repeated fights before promoting a post-retreat resume boundary; this audit is candidate runtime evidence only"
        )
    return tuple(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument("--minimum-gap-ms", type=float, default=3000.0)
    parser.add_argument("--maximum-gap-start-delay-ms", type=float, default=15000.0)
    args = parser.parse_args()
    if args.minimum_gap_ms <= 0:
        parser.error("--minimum-gap-ms must be positive")
    if args.maximum_gap_start_delay_ms < 0:
        parser.error("--maximum-gap-start-delay-ms must be non-negative")
    try:
        database_path = _resolve_database(args.database)
        lines = audit(
            database_path,
            minimum_gap_ms=args.minimum_gap_ms,
            maximum_gap_start_delay_ms=args.maximum_gap_start_delay_ms,
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
