from __future__ import annotations

"""Report source-rich encounters whose canonical encounter surfaces are still sparse.

This tool is intentionally read-only. It discovers candidates for reviewed encounter
promotion; it does not manufacture mechanics/phases from prose and it does not write
to ``data/eso.db``.
"""

import argparse
from pathlib import Path
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_content_gap_audit import audit_content_encounters


DEFAULT_DATABASE = REPO_ROOT / "data" / "eso.db"
DEFAULT_PACKET_DIR = REPO_ROOT / "data" / "encounter_evidence"


def _content_ids(connection: sqlite3.Connection, requested: tuple[str, ...]) -> tuple[str, ...]:
    if requested:
        return tuple(dict.fromkeys(value.strip() for value in requested if value.strip()))
    return tuple(
        str(row[0])
        for row in connection.execute(
            "SELECT id FROM content ORDER BY name, id"
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report encounters with source/structural data but missing canonical "
            "health, mechanics, phases, strategy, or reviewed canonical facts."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help=f"SQLite encounter database (default: {DEFAULT_DATABASE})",
    )
    parser.add_argument(
        "--packet-dir",
        type=Path,
        default=DEFAULT_PACKET_DIR,
        help=f"Encounter evidence packet directory (default: {DEFAULT_PACKET_DIR})",
    )
    parser.add_argument(
        "--content-id",
        action="append",
        default=[],
        help="Limit to one content id; may be supplied more than once.",
    )
    args = parser.parse_args()

    database = args.database.resolve()
    packet_dir = args.packet_dir.resolve()
    if not database.exists():
        parser.error(f"database does not exist: {database}")

    print("ENCOUNTER CANONICAL GAP AUDIT")
    print(f"Database:   {database}")
    print(f"Evidence:   {packet_dir}")
    print("Mode:       READ ONLY")
    print()

    total_encounters = 0
    total_gaps = 0
    with sqlite3.connect(database) as connection:
        content_ids = _content_ids(connection, tuple(args.content_id))
        for content_id in content_ids:
            try:
                audit = audit_content_encounters(
                    connection,
                    content_id=content_id,
                    packet_dir=packet_dir,
                )
            except ValueError as exc:
                print(f"[{content_id}] BLOCKED: {exc}")
                continue

            total_encounters += len(audit.database_encounters)
            gaps = audit.source_rich_canonical_gaps
            total_gaps += len(gaps)
            if not gaps:
                continue

            print(f"{audit.content_name} [{audit.content_id}]")
            for row in gaps:
                missing = ", ".join(row.missing_canonical_surfaces)
                print(
                    f"  - {row.name} [{row.encounter_id}] | "
                    f"source signals={row.source_signal_count} | missing: {missing}"
                )
            print()

    print("SUMMARY")
    print(f"Encounters inspected:             {total_encounters}")
    print(f"Source-rich canonical gaps:       {total_gaps}")
    print()
    print("BOUNDARY")
    print(
        "A reported gap is a review queue item, not permission to infer or persist "
        "missing mechanics. Promotion must remain source-backed, reviewed, and audited."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
