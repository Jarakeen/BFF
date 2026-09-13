from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_unnerving_boneyard_refresh_anomaly_service import (
    RotationUnnervingBoneyardRefreshAnomalyService,
)
from tools.discover_esologs_runtime_db import discover


def _resolve_logs_database(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    candidates = discover(
        roots=(Path(get_data_dir()), ROOT / "data", ROOT / "user_data", ROOT / "research")
    )
    preferred = [path for path in candidates if path.name == "eso_gear_customization_test.db"]
    if len(preferred) == 1:
        return preferred[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def audit(path: Path) -> int:
    report = RotationUnnervingBoneyardRefreshAnomalyService(path).inspect_anomalies()
    print("=" * 76)
    print(" UNNERVING BONEYARD REFRESH ANOMALY DRILLDOWN")
    print("=" * 76)
    print(f"Database: {path}")
    print(f"Anomalies between new cast and first new-track 117809 event: {len(report.anomalies)}")
    print()
    for index, item in enumerate(report.anomalies, start=1):
        print(
            f"{index}. report={item.report_code} fight={item.fight_id} source={item.source_id} "
            f"old_track={item.old_cast_track_id} new_track={item.new_cast_track_id}"
        )
        print(
            f"   old event after new cast: {item.old_event_after_new_cast_seconds:.6f}s "
            f"| before first new event: {item.old_event_before_first_new_seconds:.6f}s"
        )
        print(
            f"   new_cast={item.new_cast_timestamp_ms:.3f}ms "
            f"old_event={item.old_event_timestamp_ms:.3f}ms#{item.old_event_index} "
            f"first_new={item.first_new_event_timestamp_ms:.3f}ms#{item.first_new_event_index}"
        )
    if report.unresolved:
        print()
        print("Unresolved:")
        for message in report.unresolved:
            print(f"- {message}")
    print()
    print("Guardrail: this drilldown reports ordering only and does not promote refresh semantics.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Drill into the Boneyard old-track post-recast anomaly.")
    parser.add_argument("--logs-db", type=Path)
    args = parser.parse_args(argv)
    path = _resolve_logs_database(args.logs_db)
    if path is None:
        print("Could not uniquely resolve ESO Logs database; use --logs-db.")
        return 2
    return audit(path)


if __name__ == "__main__":
    raise SystemExit(main())
