from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.esologs_raw_importer import EsoLogsRawImporter
from services.paths import RAW_DATA


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import previously captured ESO Logs probe JSON files from a local directory."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DATA,
        help=f"Directory containing ESO Logs probe JSON files (default: {RAW_DATA}).",
    )
    parser.add_argument(
        "--db",
        required=True,
        help="Path to the ESO SQLite database.",
    )
    parser.add_argument(
        "--gap-ms",
        type=float,
        default=3000.0,
        help="Observed-damage gap threshold in milliseconds (default: 3000).",
    )
    args = parser.parse_args()

    raw_dir = args.raw_dir
    connection = sqlite3.connect(args.db)
    try:
        importer = EsoLogsRawImporter(connection)
        result = importer.import_directory(raw_dir, gap_threshold_ms=args.gap_ms)
        print(
            f"Imported {result['files']} raw files / {result['fights']} fights: "
            f"{result['actors']:,} actors, "
            f"{result['events']:,} events, "
            f"{result['observed_windows']:,} observed damage windows."
        )
        print(
            "Observed damage windows are heuristic evidence only; they are not "
            "authoritative boss-invulnerability or strategy phases."
        )
        return 0
    except Exception as exc:
        connection.rollback()
        print(f"ESO Logs raw import error: {exc}")
        return 2
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
