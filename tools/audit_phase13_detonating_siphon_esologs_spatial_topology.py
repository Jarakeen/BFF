from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from services.rotation_detonating_siphon_esologs_spatial_topology_service import (
    RotationDetonatingSiphonEsoLogsSpatialTopologyService,
)
from tools.discover_esologs_runtime_db import discover


SKILL_ENTITY_ID = "detonating_siphon"
CANDIDATE_ABILITY_ID = 118766


def _cast_ability_ids(canonical_database_path: Path) -> tuple[int, ...]:
    repository = SkillCoefficientRepository(canonical_database_path)
    resolution = repository.resolve_entity_id(SKILL_ENTITY_ID)
    if resolution.rank is None:
        detail = "; ".join(str(value) for value in resolution.unresolved) or "unresolved"
        raise RuntimeError(f"cannot resolve {SKILL_ENTITY_ID}: {detail}")

    values = {int(resolution.rank.base_ability_id)}
    uri = f"file:{canonical_database_path.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.execute("PRAGMA query_only = ON")
        rows = db.execute(
            "SELECT ability_id FROM skill_rank WHERE skill_id=? AND COALESCE(morph,0)=? "
            "AND ability_id IS NOT NULL",
            (int(resolution.rank.skill_id), int(resolution.rank.morph)),
        ).fetchall()
    values.update(int(row[0]) for row in rows)
    return tuple(sorted(value for value in values if value > 0))


def _logs_database(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    roots = (
        get_data_dir(),
        ROOT / "data",
        ROOT / "user_data",
        ROOT / "research",
    )
    matches = discover(roots=roots)
    if not matches:
        raise RuntimeError("no ESO Logs runtime database was found")
    if len(matches) > 1:
        rendered = "\n".join(f"  - {path}" for path in matches)
        raise RuntimeError(
            "multiple ESO Logs runtime databases were found; pass --logs-db explicitly:\n"
            + rendered
        )
    return matches[0]


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Detonating Siphon spatial-topology audit using ESO Logs actor "
            "positions. Coordinates are normalized from the documented 100x storage "
            "scale, but coordinate units are not assumed to be meters."
        )
    )
    parser.add_argument("--logs-db", help="Optional explicit imported ESO Logs SQLite corpus")
    parser.add_argument(
        "--canonical-db",
        default=str(get_data_dir() / "eso.db"),
        help="Canonical BFF ESO database used only to resolve Siphon cast ability aliases.",
    )
    parser.add_argument("--candidate-ability-id", type=int, default=CANDIDATE_ABILITY_ID)
    parser.add_argument(
        "--endpoint-radius",
        type=float,
        default=5.0,
        help=(
            "Radius threshold in normalized ESO Logs coordinate units. Defaults to 5.0 "
            "for topology comparison only; this does not assert coordinate units are meters."
        ),
    )
    args = parser.parse_args()

    try:
        logs_db = _logs_database(args.logs_db)
        canonical_db = Path(args.canonical_db)
        cast_ids = _cast_ability_ids(canonical_db)
        report = RotationDetonatingSiphonEsoLogsSpatialTopologyService(logs_db).inspect(
            cast_ability_ids=cast_ids,
            candidate_ability_id=args.candidate_ability_id,
            endpoint_radius=args.endpoint_radius,
        )
    except (RuntimeError, FileNotFoundError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print("=" * 68)
    print(" DETONATING SIPHON ESO LOGS SPATIAL TOPOLOGY")
    print("=" * 68)
    print(f"Logs database: {logs_db}")
    print(f"Canonical database: {canonical_db}")
    print(f"Cast ability ids: {', '.join(map(str, cast_ids))}")
    print(f"Candidate ability id: {report.candidate_ability_id}")
    print(f"Endpoint comparison radius: {args.endpoint_radius:g} normalized coordinate units")
    print()
    print(f"Matching cast anchors: {report.cast_count}")
    print(f"Linked candidate events: {report.linked_event_count}")
    print(f"Events with source + target positions: {report.events_with_actor_positions}")
    print(f"Events with cast-target candidate position: {report.events_with_cast_target_position}")
    print(f"Distinct cast-target candidate actors: {report.cast_target_actor_count}")
    print()
    print("Endpoint topology:")
    print(f"- within radius of caster: {report.within_radius_of_caster_count}")
    print(f"- within radius of cast-target candidate: {report.within_radius_of_cast_target_count}")
    print(f"- within radius of either endpoint: {report.within_radius_of_either_endpoint_count}")
    print(f"- beyond both endpoint radii: {report.beyond_both_endpoint_radius_count}")
    print()
    print("Observed normalized distances:")
    print(f"- median target -> caster: {_fmt(report.median_target_to_caster_distance)}")
    print(f"- median target -> cast-target candidate: {_fmt(report.median_target_to_cast_target_distance)}")
    print(f"- median target -> caster/cast-target segment: {_fmt(report.median_target_to_segment_distance)}")
    print(f"- maximum target -> caster/cast-target segment: {_fmt(report.maximum_target_to_segment_distance)}")
    print()
    print("Cast-target candidate stability:")
    print(f"- same-actor drift samples: {report.cast_target_position_stability_samples}")
    print(f"- median drift from cast position: {_fmt(report.median_cast_target_position_drift)}")

    if report.unresolved:
        print("\nUnresolved:")
        for message in report.unresolved:
            print(f"- {message}")

    print("\nInterpretation guardrails:")
    print("- ESO Logs documents x/y as actor positions stored at 100x scale.")
    print("- This audit does not assume normalized coordinate units are meters.")
    print("- The cast target is a corpse-anchor candidate, not yet proven to be the corpse entity.")
    print("- Hit observations alone do not prove the full hitbox boundary or corridor width.")
    return 0 if not report.unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
