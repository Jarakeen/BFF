from __future__ import annotations

from dataclasses import dataclass
import json
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
class RotationHealerEsoLogsSqliteObservedAbility:
    ability_game_id: int
    ability_name: str | None
    event_types: tuple[str, ...]
    event_count: int
    periodic_event_count: int


@dataclass(frozen=True)
class RotationHealerEsoLogsSqliteHealerSummary:
    report_code: str
    fight_id: int
    actor_id: int
    name: str | None
    display_name: str | None
    target_ability_names: tuple[str, ...]
    observed_abilities: tuple[RotationHealerEsoLogsSqliteObservedAbility, ...]


@dataclass(frozen=True)
class RotationHealerEsoLogsSqliteDiscoveryReport:
    database_path: str
    has_log_event: bool
    has_log_actor: bool
    fights: tuple[RotationHealerEsoLogsSqliteFightSummary, ...]
    healers: tuple[RotationHealerEsoLogsSqliteHealerSummary, ...]
    unresolved: tuple[str, ...] = ()


class RotationHealerEsoLogsSqliteDiscoveryService:
    """Inspect imported ESO Logs SQLite evidence before timing extraction.

    This service is read-only. It discovers report/fight ids and healer actors,
    records which reviewed DF-healer HoT ability ids appear, and inventories the
    healer's actual cast/heal ability ids. The inventory is diagnostic evidence,
    not a claim that every listed ability is a periodic heal or rotation skill.
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
                required_actor = {
                    "report_code",
                    "fight_id",
                    "actor_id",
                    "name",
                    "display_name",
                    "role",
                }
                missing_actor = sorted(required_actor - actor_columns)
                if missing_actor:
                    unresolved.append(
                        "log_actor is missing required columns: " + ", ".join(missing_actor)
                    )
                else:
                    target_ids = tuple(
                        target.ability_game_id
                        for target in DF_HEALER_U50_OBSERVATION_TARGETS
                    )
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
                        report_code = str(actor["report_code"])
                        fight_id = int(actor["fight_id"])
                        actor_id = int(actor["actor_id"])
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
                            (report_code, fight_id, actor_id, *target_ids),
                        ).fetchall()
                        present_names = tuple(
                            target_names[int(row["ability_game_id"])]
                            for row in present_rows
                            if int(row["ability_game_id"]) in target_names
                        )
                        observed_abilities = self._observed_abilities(
                            connection,
                            report_code=report_code,
                            fight_id=fight_id,
                            actor_id=actor_id,
                        )
                        healers.append(
                            RotationHealerEsoLogsSqliteHealerSummary(
                                report_code=report_code,
                                fight_id=fight_id,
                                actor_id=actor_id,
                                name=(
                                    str(actor["name"])
                                    if actor["name"] is not None
                                    else None
                                ),
                                display_name=(
                                    str(actor["display_name"])
                                    if actor["display_name"] is not None
                                    else None
                                ),
                                target_ability_names=present_names,
                                observed_abilities=observed_abilities,
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

    @classmethod
    def _observed_abilities(
        cls,
        connection: sqlite3.Connection,
        *,
        report_code: str,
        fight_id: int,
        actor_id: int,
    ) -> tuple[RotationHealerEsoLogsSqliteObservedAbility, ...]:
        rows = connection.execute(
            """
            SELECT ability_game_id, event_type, tick, raw_json
            FROM log_event
            WHERE report_code = ?
              AND fight_id = ?
              AND source_id = ?
              AND ability_game_id IS NOT NULL
              AND lower(event_type) IN ('cast', 'begincast', 'completecast', 'heal', 'hot')
            ORDER BY event_index
            """,
            (report_code, int(fight_id), int(actor_id)),
        ).fetchall()

        grouped: dict[int, dict] = {}
        for row in rows:
            ability_id = int(row["ability_game_id"])
            item = grouped.setdefault(
                ability_id,
                {
                    "name": None,
                    "event_types": set(),
                    "event_count": 0,
                    "periodic_event_count": 0,
                },
            )
            event_type = str(row["event_type"] or "").strip().lower()
            item["event_types"].add(event_type)
            item["event_count"] += 1
            if event_type == "hot" or bool(row["tick"]):
                item["periodic_event_count"] += 1
            if item["name"] is None:
                item["name"] = cls._ability_name_from_raw(row["raw_json"])

        abilities = [
            RotationHealerEsoLogsSqliteObservedAbility(
                ability_game_id=ability_id,
                ability_name=data["name"],
                event_types=tuple(sorted(data["event_types"])),
                event_count=int(data["event_count"]),
                periodic_event_count=int(data["periodic_event_count"]),
            )
            for ability_id, data in grouped.items()
        ]
        abilities.sort(
            key=lambda item: (
                -item.periodic_event_count,
                -item.event_count,
                item.ability_game_id,
            )
        )
        return tuple(abilities)

    @staticmethod
    def _ability_name_from_raw(raw_json: object) -> str | None:
        if raw_json is None:
            return None
        try:
            raw = json.loads(str(raw_json))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        ability = raw.get("ability")
        if isinstance(ability, dict):
            value = ability.get("name")
            if isinstance(value, str) and value.strip():
                return value.strip()
        value = raw.get("abilityName")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None
