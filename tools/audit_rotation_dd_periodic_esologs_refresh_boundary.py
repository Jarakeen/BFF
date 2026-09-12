from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_refresh_boundary_evidence_service import (
    RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceService,
)


def _common(values: tuple[float, ...], *, limit: int = 8) -> str:
    if not values:
        return "none"
    counts = Counter(round(value, 3) for value in values)
    return ", ".join(
        f"{value:g}s" + (f" x{count}" if count > 1 else "")
        for value, count in counts.most_common(limit)
    )


def audit(
    *,
    skill: str,
    database: Path,
    logs_db: Path,
    impact_id: int,
    periodic_id: int,
    active_window: float,
    tolerance_ms: float,
) -> int:
    if not database.is_file():
        print(f"Canonical ESO database not found: {database}")
        return 1
    if not logs_db.is_file():
        print(f"ESO Logs database not found or is not a file: {logs_db}")
        return 2

    report = RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceService(
        canonical_database_path=database,
        logs_database_path=logs_db,
    ).inspect(
        skill,
        impact_ability_id=impact_id,
        periodic_ability_id=periodic_id,
        active_window_seconds=active_window,
        boundary_tolerance_ms=tolerance_ms,
    )

    print()
    print("================================================")
    print(" DD PERIODIC ESO LOGS REFRESH BOUNDARY EVIDENCE")
    print("================================================")
    print(f"Skill: {report.skill_entity_id or skill}")
    print(f"Impact evidence ID:   {report.impact_ability_id}")
    print(f"Periodic evidence ID: {report.periodic_ability_id}")
    print(f"Boundary tolerance:   ±{report.boundary_tolerance_ms:g}ms")
    print(f"Consecutive impact pairs observed: {len(report.observations)}")
    print(f"Pairs with old periodic evidence: {report.observations_with_old_periodic}")
    print(f"Old periodic events at boundary: {report.old_tick_at_boundary_count}")
    print(f"Old periodic events after boundary: {report.old_tick_after_boundary_count}")
    median_last = report.median_last_old_periodic_offset_seconds
    print(
        "Median last old periodic event relative to new impact: "
        + ("unresolved" if median_last is None else f"{median_last:+.3f}s")
    )

    last_offsets = tuple(
        item.last_old_periodic_offset_seconds
        for item in report.observations
        if item.last_old_periodic_offset_seconds is not None
    )
    new_offsets = tuple(
        item.first_new_periodic_offset_seconds
        for item in report.observations
        if item.first_new_periodic_offset_seconds is not None
    )
    print(f"Common last-old offsets: {_common(last_offsets)}")
    print(f"Common first-new offsets: {_common(new_offsets)}")

    if report.unresolved:
        print("Unresolved evidence:")
        for item in report.unresolved:
            print(f"  - {item}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — this report can support review of the refresh "
        "boundary, but it never promotes executable semantics automatically."
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect cast-track-linked old periodic events around a later impact."
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--impact-id", type=int, required=True)
    parser.add_argument("--periodic-id", type=int, required=True)
    parser.add_argument("--active-window", type=float, required=True)
    parser.add_argument("--tolerance-ms", type=float, default=50.0)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return audit(
        skill=args.skill,
        database=args.database,
        logs_db=args.logs_db,
        impact_id=args.impact_id,
        periodic_id=args.periodic_id,
        active_window=args.active_window,
        tolerance_ms=args.tolerance_ms,
    )


if __name__ == "__main__":
    raise SystemExit(main())
