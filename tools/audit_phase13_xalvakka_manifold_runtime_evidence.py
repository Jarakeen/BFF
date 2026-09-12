from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.esologs_event_interpreter import EsoLogsEventInterpreter
from services.rotation_encounter_esologs_damage_observation_service import (
    RotationEncounterDamageObservationTarget,
    RotationEncounterEsoLogsDamageObservationService,
)
from tools.discover_esologs_runtime_db import discover


_CANONICAL_MECHANIC_ID = "creeping_manifold"
_DEFAULT_ABILITY_NAME = "Creeping Manifold"


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


def _default_discovery_roots() -> tuple[Path, ...]:
    return (
        get_data_dir(),
        ROOT / "data",
        ROOT / "user_data",
        ROOT / "research",
    )


def _resolve_database_path(
    explicit_database: Path | None,
    *,
    discovery_roots: tuple[Path, ...] | None = None,
) -> Path:
    if explicit_database is not None:
        return explicit_database

    roots = discovery_roots or _default_discovery_roots()
    matches = discover(roots=roots)
    if not matches:
        searched = ", ".join(str(path) for path in roots)
        raise ValueError(
            "no ESO Logs runtime database containing log_fight, log_actor, and log_event "
            f"was found under: {searched}; import ESO Logs evidence first or pass --database"
        )
    if len(matches) > 1:
        choices = ", ".join(str(path) for path in matches)
        raise ValueError(
            "multiple ESO Logs runtime databases were found; choose one explicitly with "
            f"--database: {choices}"
        )
    return matches[0]


def _fight_rows(connection: sqlite3.Connection) -> tuple[sqlite3.Row, ...]:
    rows = connection.execute(
        """
        SELECT report_code, fight_id, name, kill, difficulty, boss_percentage,
               start_time, end_time, encounter_id
        FROM log_fight
        WHERE lower(name) LIKE '%xalvakka%'
        ORDER BY report_code, fight_id
        """
    ).fetchall()
    return tuple(rows)


def _format_series(values: tuple[float, ...]) -> str:
    return ",".join(f"{value:.3f}" for value in values) if values else "none"


def audit(
    *,
    database_path: Path,
    cast_ability_ids: tuple[int, ...] = (),
    damage_ability_ids: tuple[int, ...] = (),
) -> tuple[str, ...]:
    connection = _open_read_only(database_path)
    try:
        required = ("log_fight", "log_event")
        missing = tuple(name for name in required if not _table_exists(connection, name))
        if missing:
            raise ValueError("ESO Logs runtime tables are missing: " + ", ".join(missing))

        fights = _fight_rows(connection)
        lines: list[str] = ["PHASE 13 XALVAKKA CREEPING MANIFOLD RUNTIME EVIDENCE AUDIT"]
        lines.append(f"DATABASE: {database_path}")
        lines.append(f"XALVAKKA_FIGHTS: {len(fights)}")
        if not fights:
            lines.append("MANIFOLD_OBSERVATION_READY: false")
            lines.append("UNRESOLVED: no imported Xalvakka fights exist in log_fight")
            return tuple(lines)

        interpreter = EsoLogsEventInterpreter(connection)
        observer = RotationEncounterEsoLogsDamageObservationService(interpreter)
        target = RotationEncounterDamageObservationTarget(
            canonical_mechanic_id=_CANONICAL_MECHANIC_ID,
            cast_ability_game_ids=tuple(int(value) for value in cast_ability_ids),
            cast_ability_names=(_DEFAULT_ABILITY_NAME,),
            damage_ability_game_ids=tuple(int(value) for value in damage_ability_ids),
            damage_ability_names=(_DEFAULT_ABILITY_NAME,),
        )

        candidate_count = 0
        for fight in fights:
            report_code = str(fight["report_code"])
            fight_id = int(fight["fight_id"])
            lines.append(
                "FIGHT: "
                f"report={report_code} fight_id={fight_id} name={fight['name']} "
                f"kill={fight['kill']} difficulty={fight['difficulty']} "
                f"encounter_id={fight['encounter_id']}"
            )
            report = observer.observe(
                report_code=report_code,
                fight_id=fight_id,
                target=target,
            )
            for unresolved in report.unresolved:
                lines.append(f"UNRESOLVED: report={report_code} fight_id={fight_id} {unresolved}")
            for candidate in report.candidates:
                candidate_count += 1
                first_offset = candidate.logical_damage_tick_offsets_seconds[0]
                active_width = candidate.last_damage_time_seconds - candidate.first_damage_time_seconds
                lines.append(
                    "MANIFOLD_CANDIDATE: "
                    f"report={report_code} fight_id={fight_id} "
                    f"cast_event_index={candidate.cast_event_index} "
                    f"first_hit_offset={first_offset:.3f}s "
                    f"active_width={active_width:.3f}s "
                    f"logical_ticks={_format_series(candidate.logical_damage_tick_offsets_seconds)} "
                    f"cadence={_format_series(candidate.cadence_intervals_seconds)} "
                    f"targets={candidate.observed_target_count} "
                    f"raw_damage_events={candidate.raw_damage_event_count}"
                )

        lines.append(f"MANIFOLD_CANDIDATES: {candidate_count}")
        lines.append(f"MANIFOLD_OBSERVATION_READY: {'true' if candidate_count else 'false'}")
        if candidate_count:
            lines.append(
                "REVIEW_REQUIRED: observations are candidate evidence only; compare repeated "
                "casts/fights before promoting cadence, duration, first-hit timing, or target count"
            )
        else:
            lines.append(
                "UNRESOLVED: no Creeping Manifold candidate was extracted with the reviewed "
                "display-name aliases; inspect the fight's hostile cast/damage ability aliases "
                "and rerun with --cast-ability-id / --damage-ability-id if needed"
            )
        return tuple(lines)
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect imported Xalvakka ESO Logs fights for Creeping Manifold damage cadence "
            "and target-scope candidate evidence. Read-only; no observation is promoted."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Optional ESO Logs runtime SQLite database. When omitted, the audit reuses the "
            "repository runtime-database discovery roots and requires exactly one match."
        ),
    )
    parser.add_argument(
        "--cast-ability-id",
        type=int,
        action="append",
        default=[],
        help="Optional reviewed ESO Logs cast alias; may be supplied more than once.",
    )
    parser.add_argument(
        "--damage-ability-id",
        type=int,
        action="append",
        default=[],
        help="Optional reviewed ESO Logs damage alias; may be supplied more than once.",
    )
    args = parser.parse_args()
    try:
        database_path = _resolve_database_path(args.database)
        lines = audit(
            database_path=database_path,
            cast_ability_ids=tuple(args.cast_ability_id),
            damage_ability_ids=tuple(args.damage_ability_id),
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
