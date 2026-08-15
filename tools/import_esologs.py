from __future__ import annotations

import argparse
import sqlite3

from services.esologs_client import EsoLogsClient
from services.esologs_importer import EsoLogsImporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import an ESO Logs report and record export provenance."
    )
    parser.add_argument("report_code")
    parser.add_argument("--db", required=True, help="Path to the ESO SQLite database")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    args = parser.parse_args()

    connection = sqlite3.connect(args.db)
    try:
        client = EsoLogsClient(args.client_id, args.client_secret)
        importer = EsoLogsImporter(connection, client)
        result = importer.import_report(args.report_code)
        print(
            f"Imported report {args.report_code}: "
            f"{result['fights']} fights, {result['auras']} aura records."
        )
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
