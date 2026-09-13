from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_unnerving_boneyard_refresh_boundary_evidence_service import (
    RotationUnnervingBoneyardRefreshBoundaryEvidenceService,
)
from tools.discover_esologs_runtime_db import discover


def _resolve_logs_database(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    candidates = discover(
        roots=(Path(get_data_dir()), ROOT / "data", ROOT / "user_data", ROOT / "research")
    )
    if not candidates:
        print("No ESO Logs runtime database discovered. Use --logs-db to specify one.")
        return None
    if len(candidates) > 1:
        preferred = [path for path in candidates if path.name == "eso_gear_customization_test.db"]
        if len(preferred) == 1:
            return preferred[0]
        print("Multiple ESO Logs runtime databases discovered:")
        for path in candidates:
            print(f"- {path}")
        print("Use --logs-db to choose one explicitly.")
        return None
    return candidates[0]


def _seconds(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}s"


def audit(logs_database_path: Path) -> int:
    report = RotationUnnervingBoneyardRefreshBoundaryEvidenceService(logs_database_path).inspect()

    print("=" * 76)
    print(" UNNERVING BONEYARD ESO LOGS REFRESH BOUNDARY REVIEW")
    print("=" * 76)
    print(f"Database: {logs_database_path}")
    print("Candidate periodic evidence id: 117809")
    print()
    print(f"Consecutive Boneyard cast pairs: {report.consecutive_pairs}")
    print(f"Comparable pairs with old/new 117809 tracks: {report.comparable_pairs}")
    print(f"Pairs with old-track event after new cast: {report.pairs_with_old_event_after_new_cast}")
    print(f"Pairs with old-track event at new cast timestamp: {report.pairs_with_old_event_at_new_cast}")
    print(
        "Pairs with old-track event at/after first new-track event: "
        f"{report.pairs_with_old_event_at_or_after_first_new_event}"
    )
    print(f"Exact-timestamp old events at new cast: {report.exact_timestamp_old_events_at_new_cast}")
    print(
        "Median last-old -> new-cast gap: "
        f"{_seconds(report.median_last_old_before_new_cast_seconds)}"
    )
    print(
        "Median new-cast -> first-new-event gap: "
        f"{_seconds(report.median_first_new_after_new_cast_seconds)}"
    )

    if report.unresolved:
        print()
        print("Unresolved:")
        for message in report.unresolved:
            print(f"- {message}")

    print()
    print("Interpretation guardrails:")
    print("- zero old events after new cast supports cast-time replacement observationally")
    print("- old events after cast but before first new event support only first-new-event replacement")
    print("- exact timestamp ordering uses ESO Logs event_index when available")
    print("- this audit never promotes executable refresh semantics automatically")
    return 0 if report.comparable_pairs else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review Unnerving Boneyard 117809 replacement timing across consecutive casts."
    )
    parser.add_argument("--logs-db", type=Path)
    args = parser.parse_args(argv)
    path = _resolve_logs_database(args.logs_db)
    if path is None:
        return 2
    return audit(path)


if __name__ == "__main__":
    raise SystemExit(main())
