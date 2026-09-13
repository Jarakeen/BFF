from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_unnerving_boneyard_first_tick_stability_service import (
    RotationUnnervingBoneyardFirstTickStabilityService,
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
    report = RotationUnnervingBoneyardFirstTickStabilityService(logs_database_path).inspect()
    print("=" * 76)
    print(" UNNERVING BONEYARD FIRST-TICK STABILITY REVIEW")
    print("=" * 76)
    print(f"Database: {logs_database_path}")
    print("Candidate periodic evidence id: 117809")
    print()
    print(f"Samples: {report.sample_count}")
    print(f"Median: {_seconds(report.median_offset_seconds)}")
    print(f"P10: {_seconds(report.p10_offset_seconds)}")
    print(f"P90: {_seconds(report.p90_offset_seconds)}")
    print(f"Minimum: {_seconds(report.minimum_offset_seconds)}")
    print(f"Maximum: {_seconds(report.maximum_offset_seconds)}")

    if report.groups:
        print()
        print("Per report/source groups:")
        for group in report.groups:
            print(
                f"- report={group.report_code} source={group.source_id} n={group.sample_count} "
                f"median={group.median_offset_seconds:.4f}s "
                f"range={group.minimum_offset_seconds:.4f}-{group.maximum_offset_seconds:.4f}s"
            )

    if report.unresolved:
        print()
        print("Unresolved:")
        for message in report.unresolved:
            print(f"- {message}")

    print()
    print("Guardrail: this audit measures observational cast-to-first-damage timing only; it does not promote exact first-tick semantics.")
    return 0 if report.sample_count else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review Unnerving Boneyard cast-to-first-117809 timing stability.")
    parser.add_argument("--logs-db", type=Path)
    args = parser.parse_args(argv)
    path = _resolve_logs_database(args.logs_db)
    if path is None:
        return 2
    return audit(path)


if __name__ == "__main__":
    raise SystemExit(main())
