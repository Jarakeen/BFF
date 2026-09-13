from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.rotation_meteor_esologs_raw_identity_service import (
    RotationMeteorEsoLogsRawIdentityService,
)
from tools.discover_esologs_runtime_db import discover


def _resolve_logs_database(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    candidates = discover(
        (
            Path(get_data_dir()),
            ROOT / "data",
            ROOT / "user_data",
            ROOT / "research",
        )
    )
    if not candidates:
        print("No ESO Logs runtime database discovered. Use --logs-db to specify one.")
        return None
    if len(candidates) > 1:
        print("Multiple ESO Logs runtime databases discovered:")
        for path in candidates:
            print(f"- {path}")
        print("Use --logs-db to choose one explicitly.")
        return None
    return candidates[0]


def audit(logs_database_path: Path) -> int:
    report = RotationMeteorEsoLogsRawIdentityService(logs_database_path).inspect()

    print("=" * 68)
    print(" METEOR FAMILY RAW ESO LOGS IDENTITY AUDIT")
    print("=" * 68)
    print(f"Database: {logs_database_path}")
    print("Names: Meteor | Ice Comet | Shooting Star")
    print(f"Matching raw events: {report.matching_event_count}")
    print(f"Matching cast-like events: {report.matching_cast_event_count}")
    print()
    print("Observed identities:")
    if not report.rows:
        print("- none")
    else:
        for row in report.rows:
            ability_id = str(row.ability_game_id) if row.ability_game_id is not None else "none"
            print(
                f"- {row.ability_name} | id={ability_id} | type={row.event_type or '(blank)'} "
                f"| events={row.event_count} | sources={row.source_actor_count} "
                f"| cast-track-linked={row.cast_track_linked_event_count}"
            )

    if report.unresolved:
        print()
        print("Unresolved:")
        for message in report.unresolved:
            print(f"- {message}")

    print()
    print("Interpretation guardrails:")
    print("- raw ability names and numeric ids are discovery evidence only")
    print("- this audit bypasses the canonical Meteor crosswalk on purpose")
    print("- observed ids are not promoted into runtime semantics automatically")
    return 0 if report.rows else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventory raw ESO Logs identities for Meteor, Ice Comet, and Shooting Star."
    )
    parser.add_argument(
        "--logs-db",
        type=Path,
        help="Optional explicit ESO Logs SQLite database. Auto-discovered when omitted.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logs_db = _resolve_logs_database(args.logs_db)
    if logs_db is None:
        return 2
    return audit(logs_db)


if __name__ == "__main__":
    raise SystemExit(main())
