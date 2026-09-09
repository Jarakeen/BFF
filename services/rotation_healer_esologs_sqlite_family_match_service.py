from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from services.rotation_healer_esologs_ability_family_service import (
    RotationHealerEsoLogsAbilityFamilyService,
)
from services.rotation_healer_esologs_observation_extractor import (
    DF_HEALER_U50_OBSERVATION_TARGETS,
)


@dataclass(frozen=True)
class RotationHealerEsoLogsSqliteFamilyMatch:
    report_code: str
    fight_id: int
    actor_id: int
    source_name: str
    matched_ability_ids: tuple[int, ...]
    event_count: int
    periodic_event_count: int


@dataclass(frozen=True)
class RotationHealerEsoLogsSqliteFamilyMatchReport:
    log_database_path: str
    canonical_database_path: str
    matches: tuple[RotationHealerEsoLogsSqliteFamilyMatch, ...]
    unresolved: tuple[str, ...]


class RotationHealerEsoLogsSqliteFamilyMatchService:
    """Match historical ESO Logs healer events to canonical skill families.

    Exact max-rank ability ids are too brittle for historical logs because ESO
    Logs can emit another rank/member id from the same skill family. This audit
    uses current canonical ``skill`` + ``skill_rank`` identity only; it does not
    infer that unrelated historical abilities are equivalent by cadence or name.
    """

    def inspect(
        self,
        log_database_path: str | Path,
        canonical_database_path: str | Path,
    ) -> RotationHealerEsoLogsSqliteFamilyMatchReport:
        log_path = Path(log_database_path)
        canonical_path = Path(canonical_database_path)
        if not log_path.exists():
            raise FileNotFoundError(log_path)
        if not canonical_path.exists():
            raise FileNotFoundError(canonical_path)

        family_service = RotationHealerEsoLogsAbilityFamilyService(canonical_path)
        families = {}
        unresolved: list[str] = []
        for target in DF_HEALER_U50_OBSERVATION_TARGETS:
            family = family_service.resolve(target.source_name)
            if family is None:
                unresolved.append(
                    f"{target.source_name}: canonical skill family could not be resolved"
                )
                continue
            families[target.source_name] = family

        uri = f"file:{log_path.resolve().as_posix()}?mode=ro"
        matches: list[RotationHealerEsoLogsSqliteFamilyMatch] = []
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if not {"log_event", "log_actor"}.issubset(tables):
                missing = sorted({"log_event", "log_actor"} - tables)
                unresolved.append("log database missing tables: " + ", ".join(missing))
                return RotationHealerEsoLogsSqliteFamilyMatchReport(
                    log_database_path=str(log_path),
                    canonical_database_path=str(canonical_path),
                    matches=(),
                    unresolved=tuple(dict.fromkeys(unresolved)),
                )

            healers = connection.execute(
                """
                SELECT report_code, fight_id, actor_id
                FROM log_actor
                WHERE lower(COALESCE(role, '')) = 'healer'
                ORDER BY report_code, fight_id, actor_id
                """
            ).fetchall()

            for healer in healers:
                report_code = str(healer["report_code"])
                fight_id = int(healer["fight_id"])
                actor_id = int(healer["actor_id"])
                for source_name, family in families.items():
                    placeholders = ",".join("?" for _ in family.ability_game_ids)
                    rows = connection.execute(
                        f"""
                        SELECT ability_game_id,
                               COUNT(*) AS event_count,
                               SUM(CASE WHEN lower(event_type) = 'hot' OR COALESCE(tick, 0) != 0 THEN 1 ELSE 0 END)
                                   AS periodic_event_count
                        FROM log_event
                        WHERE report_code = ?
                          AND fight_id = ?
                          AND source_id = ?
                          AND ability_game_id IN ({placeholders})
                          AND lower(event_type) IN ('cast', 'begincast', 'completecast', 'heal', 'hot')
                        GROUP BY ability_game_id
                        ORDER BY ability_game_id
                        """,
                        (
                            report_code,
                            fight_id,
                            actor_id,
                            *family.ability_game_ids,
                        ),
                    ).fetchall()
                    if not rows:
                        continue
                    matches.append(
                        RotationHealerEsoLogsSqliteFamilyMatch(
                            report_code=report_code,
                            fight_id=fight_id,
                            actor_id=actor_id,
                            source_name=source_name,
                            matched_ability_ids=tuple(int(row["ability_game_id"]) for row in rows),
                            event_count=sum(int(row["event_count"] or 0) for row in rows),
                            periodic_event_count=sum(
                                int(row["periodic_event_count"] or 0) for row in rows
                            ),
                        )
                    )

        return RotationHealerEsoLogsSqliteFamilyMatchReport(
            log_database_path=str(log_path),
            canonical_database_path=str(canonical_path),
            matches=tuple(matches),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
