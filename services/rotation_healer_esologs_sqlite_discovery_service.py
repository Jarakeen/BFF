from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from services.rotation_healer_esologs_observation_extractor import (
    DF_HEALER_U50_OBSERVATION_TARGETS,
)


@dataclass(frozen=True)
class RotationHealerEsoLogsSqliteFightSummary:
    report_code: str
    fight_id: int
    event_count: int
    first_timestamp: float | None
    last_timestamp: float | None


@dataclass(frozen=True)
class RotationHealerEsoLogsSqliteHealerSummary:
    report_code: str
    fight_id: int
    actor_id: int
    name: str | None
    display_name: str | None
    target_ability_names: tuple[str, ...]


@dataclass(frozen=True)
class RotationHealerEsoLogsSqliteDiscoveryReport:
    database_path: str
    has_log_event: bool
    has_log_actor: bool
    fights: tuple[RotationHealerEsoLogsSqliteFightSummary, ...]
    healers: tuple[RotationHealerEsoLogsSqliteHealerSummary, ...]
    unresolved: tuple[str, ...] = ()


class RotationHealerEsoLogsSqliteDiscoveryService:
    """Inspect an imported ESO Logs SQLite database before timing extraction.

    This service is read-only. It discovers report/fight ids and healer actors,
    and records which of the reviewed DF-healer HoT ability ids actually appear
    in each healer's source events. It does not infer timing semantics.
    """

    REQUIRED_LOG_EVENT_COLUMNS = {
        "report_code",
        "fight_id",
        "event_index",
        "timestamp",
        "event_type",
        "source_id",
        "ability_game_id",
        "tick",
        "raw_json",
    }

    def inspect(self, database_path: str | Path) -> RotationHealerEsoLogsSqliteDiscoveryReport:
        path = Path(database_path)
        if not path.exists():
            raise FileNotFoundError(path)

        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            has_log_event = "log_event" in tables
            has_log_actor = "log_actor" in tables
            unresolved: list[str] = []

            if not has_log_event:
                return RotationHealerEsoLogsSqliteDiscoveryReport(
                    database_path=str(path),
                    has_log_event=False,
                    has_log_actor=has_log_actor,
                    fights=(),
                    healers=(),
                    unresolved=("log_event table is unavailable",),
                )

            event_columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(log_event)").fetchall()
            }
            missing = sorted(self.REQUIRED_LOG_EVENT_COLUMNS - event_columns)
            if missing:
                unresolved.append(
                    "log_event is missing required columns: " + ", ".join(missing)
                )

            fights = tuple(
                RotationHealerEsoLogsSqliteFightSummary(
                    report_code=str(row["report_code"]),
                    fight_id=int(row["fight_id"]),
                    event_count=int(row["event_count"]),
                    first_timestamp=(
                        float(row["first_timestamp"])
                        if row["first_timestamp"] is not None
                        else None
                    ),
                    last_timestamp=(
                        float(row["last_timestamp"])
                        if row["last_timestamp"] is not None
                        else None
                    ),
                )
                for row in connection.execute(
                    """
                    SELECT report_code, fight_id, COUNT(*) AS event_count,
                           MIN(timestamp) AS first_timestamp,
                           MAX(timestamp) AS last_timestamp
                    FROM log_event
                    GROUP BY report_code, fight_id
                    ORDER BY report_code, fight_id
                    """
                ).fetchall()
            )

            healers: list[RotationHealerEsoLogsSqliteHealerSummary] = []
            if not has_log_actor:
                unresolved.append("log_actor table is unavailable; healer roles cannot be discovered")
            else:
                actor_columns = {
                    str(row[1])
                    for row in connection.execute("PRAGMA table_info(log_actor)").fetchall()
                }
                required_actor = {"report_code", "fight_id", "actor_id", "name", "display_name", "role"}
                missing_actor = sorted(required_actor - actor_columns)
                if missing_actor:
                    unresolved.append(
                        "log_actor is missing required columns: " + ", ".join(missing_actor)
                    )
                else:
                    target_ids = tuple(target.ability_game_id for target in DF_HEALER_U50_OBSERVATION_TARGETS)
                    target_names = {
                        target.ability_game_id: target.source_name
                        for target in DF_HEALER_U50_OBSERVATION_TARGETS
                    }
                    placeholders = ",".join("?" for _ in target_ids)
                    actor_rows = connection.execute(
                        """
                        SELECT report_code, fight_id, actor_id, name, display_name
                        FROM log_actor
                        WHERE lower(COALESCE(role, '')) = 'healer'
                        ORDER BY report_code, fight_id, actor_id
                        """
                    ).fetchall()
                    for actor in actor_rows:
                        present_rows = connection.execute(
                            f"""
                            SELECT DISTINCT ability_game_id
                            FROM log_event
                            WHERE report_code = ?
                              AND fight_id = ?
                              AND source_id = ?
                              AND ability_game_id IN ({placeholders})
                            ORDER BY ability_game_id
                            """,
                            (
                                actor["report_code"],
                                int(actor["fight_id"]),
                                int(actor["actor_id"]),
                                *target_ids,
                            ),
                        ).fetchall()
                        present_names = tuple(
                            target_names[int(row["ability_game_id"])]
                            for row in present_rows
                            if int(row["ability_game_id"]) in target_names
                        )
                        healers.append(
                            RotationHealerEsoLogsSqliteHealerSummary(
                                report_code=str(actor["report_code"]),
                                fight_id=int(actor["fight_id"]),
                                actor_id=int(actor["actor_id"]),
                                name=(str(actor["name"]) if actor["name"] is not None else None),
                                display_name=(
                                    str(actor["display_name"])
                                    if actor["display_name"] is not None
                                    else None
                                ),
                                target_ability_names=present_names,
                            )
                        )

        return RotationHealerEsoLogsSqliteDiscoveryReport(
            database_path=str(path),
            has_log_event=has_log_event,
            has_log_actor=has_log_actor,
            fights=fights,
            healers=tuple(healers),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
