from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.esologs_client import EsoLogsClient
from services.esologs_combat_importer import EsoLogsCombatImporter
from services.settings_service import SettingsService


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import raw ESO Logs combat evidence, including actors, events, "
            "and observed damage windows."
        )
    )
    parser.add_argument("report_code", help="ESO Logs report code or report URL")
    parser.add_argument("--db", required=True, help="Path to the ESO SQLite database")
    parser.add_argument(
        "--fight",
        dest="fights",
        action="append",
        type=int,
        help="Fight ID to import. Repeat for multiple fights. If omitted, import all fights.",
    )
    parser.add_argument(
        "--settings",
        default="settings.json",
        help="BFF settings path. ESO Logs secret is loaded from the OS keyring.",
    )
    parser.add_argument(
        "--gap-ms",
        type=float,
        default=3000.0,
        help="Gap used by the observed-damage-window heuristic (default: 3000 ms).",
    )
    args = parser.parse_args()

    settings = SettingsService(Path(args.settings)).load()
    client = EsoLogsClient(
        client_id=settings.get("EsoLogsClientId", ""),
        client_secret=settings.get("EsoLogsClientSecret", ""),
    )

    connection = sqlite3.connect(args.db)
    try:
        importer = EsoLogsCombatImporter(connection, client)
        result = importer.import_report(
            args.report_code,
            fight_ids=args.fights,
            gap_threshold_ms=args.gap_ms,
        )
        print(
            f"Imported {result['fights']} fights: "
            f"{result['actors']:,} actors, "
            f"{result['events']:,} events, "
            f"{result['observed_windows']:,} observed damage windows."
        )
        print(
            "Observed damage windows are a heuristic for analysis, not authoritative "
            "boss-invulnerability intervals."
        )
        return 0
    except Exception as exc:
        print(f"ESO Logs import error: {exc}")
        return 2
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
