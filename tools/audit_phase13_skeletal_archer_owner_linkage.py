from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_skeletal_archer_owner_linkage_evidence_service import (
    RotationSkeletalArcherOwnerLinkageEvidenceService,
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


def audit(logs_database_path: Path) -> int:
    report = RotationSkeletalArcherOwnerLinkageEvidenceService(logs_database_path).inspect()
    print("=" * 76)
    print(" SKELETAL ARCHER PET OWNER-LINKAGE ADEQUACY REVIEW")
    print("=" * 76)
    print(f"Database: {logs_database_path}")
    print(f"Candidate periodic evidence id: {report.periodic_ability_id}")
    print(f"Candidate damage events: {report.event_count}")
    print(f"Distinct candidate source actors: {report.source_actor_count}")
    print()
    print("log_actor columns:")
    if report.log_actor_columns:
        print("  " + ", ".join(report.log_actor_columns))
    else:
        print("  none / table unavailable")
    print("Explicit linkage-like actor columns:")
    if report.actor_linkage_columns:
        for value in report.actor_linkage_columns:
            print(f"  - {value}")
    else:
        print("  none")
    print("Raw JSON linkage-like paths observed on candidate events:")
    if report.raw_linkage_paths:
        for value in report.raw_linkage_paths:
            print(f"  - {value}")
        print(f"Candidate events carrying at least one linkage-like path: {report.raw_linkage_sample_count}")
    else:
        print("  none")
    print()
    print(
        "Imported linkage evidence present: "
        + ("YES — requires manual semantic review" if report.has_imported_linkage_evidence else "NO")
    )
    if report.unresolved:
        print()
        print("Unresolved:")
        for item in report.unresolved:
            print(f"- {item}")
    print()
    print(
        "Guardrail: timing/window co-occurrence is not owner linkage. This audit only asks "
        "whether the imported schema or raw event metadata exposes explicit relationship hints."
    )
    return 0 if report.event_count else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect imported ESO Logs metadata for Skeletal Archer pet-to-owner linkage hints."
    )
    parser.add_argument("--logs-db", type=Path)
    args = parser.parse_args(argv)
    path = _resolve_logs_database(args.logs_db)
    if path is None:
        return 2
    return audit(path)


if __name__ == "__main__":
    raise SystemExit(main())
