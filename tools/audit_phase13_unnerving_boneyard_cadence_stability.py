from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_unnerving_boneyard_cadence_stability_service import (
    RotationUnnervingBoneyardCadenceStabilityService,
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
    preferred = [path for path in candidates if path.name == "eso_gear_customization_test.db"]
    if len(preferred) == 1:
        return preferred[0]
    if len(candidates) == 1:
        return candidates[0]
    print("Multiple ESO Logs runtime databases discovered:")
    for path in candidates:
        print(f"- {path}")
    print("Use --logs-db to choose one explicitly.")
    return None


def _seconds(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}s"


def audit(logs_database_path: Path) -> int:
    report = RotationUnnervingBoneyardCadenceStabilityService(logs_database_path).inspect()
    print("=" * 76)
    print(" UNNERVING BONEYARD NORMALIZED CADENCE REVIEW")
    print("=" * 76)
    print(f"Database: {logs_database_path}")
    print("Candidate periodic evidence id: 117809")
    print("Collapse tolerance: 10ms | near-1s tolerance: ±0.08s")
    print()
    print(f"Tracks: {report.track_count}")
    print(f"Normalized occurrences: {report.occurrence_count}")
    print(f"Adjacent intervals: {report.interval_count}")
    print(f"Median interval: {_seconds(report.median_interval_seconds)}")
    print(f"P10: {_seconds(report.p10_interval_seconds)}")
    print(f"P90: {_seconds(report.p90_interval_seconds)}")
    print(f"Minimum: {_seconds(report.minimum_interval_seconds)}")
    print(f"Maximum: {_seconds(report.maximum_interval_seconds)}")
    if report.near_one_second_fraction is None:
        fraction = "n/a"
    else:
        fraction = f"{report.near_one_second_fraction:.1%}"
    print(f"Intervals within 1.0s ±0.08s: {report.near_one_second_count} ({fraction})")

    if report.unresolved:
        print()
        print("Unresolved:")
        for message in report.unresolved:
            print(f"- {message}")

    print()
    print("Guardrail: normalized recurrence is observational evidence only; this audit does not promote executable cadence.")
    return 0 if report.interval_count else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review normalized Unnerving Boneyard 117809 recurrence cadence."
    )
    parser.add_argument("--logs-db", type=Path)
    args = parser.parse_args(argv)
    path = _resolve_logs_database(args.logs_db)
    if path is None:
        return 2
    return audit(path)


if __name__ == "__main__":
    raise SystemExit(main())
