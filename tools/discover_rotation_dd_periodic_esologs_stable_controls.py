from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from minmax.skill_coefficient_repository import ability_entity_id
from services.rotation_dd_periodic_esologs_magnitude_state_transition_service import (
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport,
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionService,
)


_CAST_TYPES = ("cast", "completecast", "begincast")


@dataclass(frozen=True)
class StableControlGroup:
    report_code: str
    fight_id: int
    source_id: int
    cast_count: int
    report: RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport

    @property
    def stable_pairs(self) -> int:
        return self.report.state_same_amount_changed + self.report.state_same_amount_constant


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
    return value.strip() if isinstance(value, str) and value.strip() else None


def _cast_groups(
    *,
    service: RotationDDPeriodicEsoLogsMagnitudeStateTransitionService,
    skill_entity_id: str,
) -> tuple[tuple[str, int, int, int], ...]:
    identity = ability_entity_id(skill_entity_id)
    resolution = service.coefficients.resolve_entity_id(identity)
    aliases: set[int] = set()
    if resolution.rank is not None:
        aliases.update(
            service._numeric_aliases(
                resolution.rank.skill_id,
                resolution.rank.morph,
                resolution.rank.base_ability_id,
            )
        )

    uri = f"file:{service.logs_database_path.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only = ON")
        rows = db.execute(
            "SELECT report_code,fight_id,source_id,event_type,ability_game_id,raw_json "
            "FROM log_event WHERE lower(event_type) IN ('cast','begincast','completecast') "
            "AND source_id IS NOT NULL ORDER BY report_code,fight_id,source_id"
        ).fetchall()

    matched: list[sqlite3.Row] = []
    for row in rows:
        raw_name = _ability_name_from_raw(row["raw_json"])
        if raw_name:
            if ability_entity_id(raw_name) == identity:
                matched.append(row)
            continue
        value = row["ability_game_id"]
        if value is not None and int(value) in aliases:
            matched.append(row)

    if not matched:
        return ()

    anchor_type = next(
        kind for kind in _CAST_TYPES if any(str(row["event_type"] or "").strip().lower() == kind for row in matched)
    )
    counts: dict[tuple[str, int, int], int] = {}
    for row in matched:
        if str(row["event_type"] or "").strip().lower() != anchor_type:
            continue
        key = (str(row["report_code"]), int(row["fight_id"]), int(row["source_id"]))
        counts[key] = counts.get(key, 0) + 1
    return tuple((*key, count) for key, count in sorted(counts.items()))


def rank_stable_controls(groups: tuple[StableControlGroup, ...]) -> tuple[StableControlGroup, ...]:
    return tuple(
        sorted(
            groups,
            key=lambda item: (
                -item.stable_pairs,
                -item.report.state_same_amount_constant,
                item.report.state_same_amount_changed,
                -item.report.comparable_occurrence_pairs,
                item.report.ambiguous_occurrence_clusters,
                item.report_code,
                item.fight_id,
                item.source_id,
            ),
        )
    )


def discover(
    *,
    skill: str,
    periodic_id: int,
    database: Path,
    logs_db: Path,
    max_results: int,
    minimum_pairs: int,
) -> int:
    if not database.is_file():
        print(f"Canonical ESO database not found: {database}")
        return 1
    if not logs_db.is_file():
        print(f"ESO Logs database not found or is not a file: {logs_db}")
        return 2

    service = RotationDDPeriodicEsoLogsMagnitudeStateTransitionService(
        canonical_database_path=database,
        logs_database_path=logs_db,
    )
    cast_groups = _cast_groups(service=service, skill_entity_id=skill)
    if not cast_groups:
        print(f"No matching cast groups found for {ability_entity_id(skill) or skill}.")
        return 0

    print()
    print("===============================================")
    print(" DD PERIODIC ESO LOGS STABLE CONTROL DISCOVERY")
    print("===============================================")
    print(f"Skill: {ability_entity_id(skill) or skill}")
    print(f"Periodic evidence ID: {periodic_id}")
    print(f"Cast groups discovered: {len(cast_groups)}")
    print("Scanning groups for clean state-same occurrence pairs...")

    results: list[StableControlGroup] = []
    for report_code, fight_id, source_id, cast_count in cast_groups:
        report = service.inspect(
            skill,
            periodic_ability_id=periodic_id,
            report_code=report_code,
            fight_id=fight_id,
            source_id=source_id,
        )
        if report.comparable_occurrence_pairs < max(1, int(minimum_pairs)):
            continue
        results.append(
            StableControlGroup(
                report_code=report_code,
                fight_id=fight_id,
                source_id=source_id,
                cast_count=cast_count,
                report=report,
            )
        )

    ranked = rank_stable_controls(tuple(results))
    useful = tuple(item for item in ranked if item.stable_pairs > 0)

    print(f"Comparable groups: {len(ranked)}")
    print(f"Groups with at least one state-same pair: {len(useful)}")
    print()
    if not useful:
        print("No stable-state control groups were found in the current corpus.")
    else:
        print("Best stable-state controls:")
        for index, item in enumerate(useful[: max(0, int(max_results))], start=1):
            report = item.report
            print(
                f"  [{index}] report={item.report_code} fight={item.fight_id} "
                f"source={item.source_id} casts={item.cast_count}"
            )
            print(
                f"      comparable={report.comparable_occurrence_pairs} "
                f"ambiguous={report.ambiguous_occurrence_clusters}"
            )
            print(
                "      state changed + amount changed/constant: "
                f"{report.state_changed_amount_changed}/{report.state_changed_amount_constant}"
            )
            print(
                "      state same    + amount changed/constant: "
                f"{report.state_same_amount_changed}/{report.state_same_amount_constant}"
            )

    print()
    print(
        "Result: DISCOVERY ONLY — groups are ranked for magnitude-policy review. "
        "Numeric IDs remain observational evidence handles and no runtime semantic is promoted."
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Find ESO Logs report/fight/source groups with clean same-cast periodic "
            "occurrence pairs whose reconstructed source/target state stays unchanged."
        )
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--periodic-id", type=int, required=True)
    parser.add_argument("--max-results", type=int, default=12)
    parser.add_argument("--minimum-pairs", type=int, default=2)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return discover(
        skill=args.skill,
        periodic_id=args.periodic_id,
        database=args.database,
        logs_db=args.logs_db,
        max_results=args.max_results,
        minimum_pairs=args.minimum_pairs,
    )


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["StableControlGroup", "rank_stable_controls"]
