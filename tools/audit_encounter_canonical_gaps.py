from __future__ import annotations

"""Report actionable canonical encounter gaps without flattening the whole corpus.

This tool is intentionally read-only. By default it reports encounters that already
have an encounter-evidence packet with reconciled facts and still lack canonical
surfaces. Use ``--include-structural-backlog`` to include the much larger source-rich
structural backlog. The tool never infers or writes encounter truth.
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
        for row in connection.execute("SELECT id FROM content ORDER BY name, id")
    )


def _review_backed_rows(audit):
    packet_by_id = {
        gap.encounter_id: gap
        for gap in audit.packet_gaps
        if gap.reconciled_facts > 0
    }
    return tuple(
        (row, packet_by_id[row.encounter_id])
        for row in audit.source_rich_canonical_gaps
        if row.encounter_id in packet_by_id
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report actionable encounter canonical gaps. Default output is limited "
            "to source-rich encounters that already have reviewed/reconcilable "
            "encounter-evidence packets."
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
    parser.add_argument(
        "--include-structural-backlog",
        action="store_true",
        help=(
            "Also print source-rich encounters that do not yet have an encounter "
            "evidence packet. This is intentionally noisy for corpus planning."
        ),
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
    print(
        "Scope:      ACTIONABLE REVIEW QUEUE"
        if not args.include_structural_backlog
        else "Scope:      ACTIONABLE REVIEW QUEUE + STRUCTURAL BACKLOG"
    )
    print()

    total_encounters = 0
    total_actionable = 0
    total_structural = 0
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
            actionable = _review_backed_rows(audit)
            actionable_ids = {row.encounter_id for row, _gap in actionable}
            structural = tuple(
                row
                for row in audit.source_rich_canonical_gaps
                if row.encounter_id not in actionable_ids
            )
            total_actionable += len(actionable)
            total_structural += len(structural)

            if not actionable and not (args.include_structural_backlog and structural):
                continue

            print(f"{audit.content_name} [{audit.content_id}]")
            for row, gap in actionable:
                missing = ", ".join(row.missing_canonical_surfaces)
                queue = []
                if gap.missing_eligible:
                    queue.append(f"eligible={len(gap.missing_eligible)}")
                if gap.review_required:
                    queue.append(f"review={len(gap.review_required)}")
                if gap.blocked:
                    queue.append(f"blocked={len(gap.blocked)}")
                queue_text = ", ".join(queue) or "packet facts present"
                print(
                    f"  [ACTIONABLE] {row.name} [{row.encounter_id}] | "
                    f"source signals={row.source_signal_count} | "
                    f"evidence facts={gap.reconciled_facts} ({queue_text}) | "
                    f"missing: {missing}"
                )

            if args.include_structural_backlog:
                for row in structural:
                    missing = ", ".join(row.missing_canonical_surfaces)
                    print(
                        f"  [STRUCTURAL] {row.name} [{row.encounter_id}] | "
                        f"source signals={row.source_signal_count} | missing: {missing}"
                    )
            print()

    print("SUMMARY")
    print(f"Encounters inspected:             {total_encounters}")
    print(f"Actionable review-backed gaps:    {total_actionable}")
    print(f"Structural backlog gaps:          {total_structural}")
    if not args.include_structural_backlog:
        print("Structural backlog printed:       no (use --include-structural-backlog)")
    print()
    print("BOUNDARY")
    print(
        "A reported gap is a review queue item, not permission to infer or persist "
        "missing mechanics. Promotion must remain source-backed, reviewed, and audited."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
