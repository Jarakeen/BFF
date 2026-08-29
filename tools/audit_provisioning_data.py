from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE


SOURCE_DIRECTORIES = (
    ROOT / "data" / "raw",
    ROOT / "data" / "processed",
)
RECORD_KEYS = (
    "minedItemSummary",
    "minedItem",
    "foods",
    "drinks",
    "records",
)


def _matching_source_files() -> list[Path]:
    paths: list[Path] = []
    for directory in SOURCE_DIRECTORIES:
        if not directory.exists():
            continue
        paths.extend(
            path
            for path in directory.glob("*.json")
            if "food" in path.name.casefold() or "drink" in path.name.casefold()
        )
    return sorted(paths, key=lambda path: str(path).casefold())


def _record_groups(payload: Any) -> list[tuple[str, list[dict[str, Any]]]]:
    if isinstance(payload, list):
        return [
            (
                "(root list)",
                [record for record in payload if isinstance(record, dict)],
            )
        ]
    if not isinstance(payload, dict):
        return []

    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for key in RECORD_KEYS:
        records = payload.get(key)
        if isinstance(records, list):
            groups.append(
                (key, [record for record in records if isinstance(record, dict)])
            )
    return groups


def _clockwork_matches(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if "clockwork citrus" in str(record.get("name") or "").casefold()
    ]


def _description(record: dict[str, Any]) -> str:
    containers = [record]
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        containers.append(metadata)
    for container in containers:
        for key in (
            "abilityDesc",
            "ability_desc",
            "ability_description",
            "description",
            "effect_description",
        ):
            value = container.get(key)
            if value:
                return str(value)
    return ""


def _audit_file(path: Path) -> None:
    print()
    print(f"Source file: {path}")
    print(f"  Bytes:     {path.stat().st_size:,}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"  SHA-256:   {digest}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"  ERROR:     {exc}")
        return

    if isinstance(payload, dict):
        print(f"  Root keys: {', '.join(sorted(str(key) for key in payload))}")
        if "numRecords" in payload:
            print(f"  Declared:  {payload['numRecords']}")
    else:
        print(f"  Root type: {type(payload).__name__}")

    groups = _record_groups(payload)
    if not groups:
        print("  Records:   no supported record collection found")
        return

    for key, records in groups:
        print(f"  Collection {key}: {len(records):,} object records")
        matches = _clockwork_matches(records)
        print(f"    Clockwork Citrus matches: {len(matches):,}")
        for match in matches[:5]:
            print(
                "      "
                f"name={match.get('name')!r} | "
                f"itemId={match.get('itemId')!r} | "
                f"id={match.get('id')!r} | "
                f"type={match.get('type')!r} | "
                f"craftType={match.get('craftType')!r}"
            )
            description = _description(match)
            print(
                "      description="
                + (description[:500] if description else "(none in supported fields)")
            )


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def _audit_database(path: Path) -> bool:
    print()
    print(f"Database: {path}")
    if not path.exists():
        print("  ERROR: database not found")
        return False

    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        tables = [
            str(row["name"])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type IN ('table', 'view')
                  AND (
                    lower(name) LIKE '%food%'
                    OR lower(name) LIKE '%drink%'
                    OR lower(name) LIKE '%provision%'
                  )
                ORDER BY name
                """
            )
        ]
        print(
            "  Provisioning tables/views: "
            + (", ".join(tables) if tables else "(none)")
        )

        if not _table_exists(connection, "entity"):
            print("  entity table: unavailable")
            return True

        counts = connection.execute(
            """
            SELECT entity_type, COUNT(*) AS count
            FROM entity
            WHERE entity_type IN ('food', 'drink', 'provisioning')
            GROUP BY entity_type
            ORDER BY entity_type
            """
        ).fetchall()
        if counts:
            for row in counts:
                print(f"  {row['entity_type']} entities: {row['count']:,}")
        else:
            print("  Food/drink/provisioning entities: 0")

        matches = connection.execute(
            """
            SELECT id, entity_type, name, slug
            FROM entity
            WHERE lower(name) LIKE '%clockwork%citrus%'
               OR lower(slug) LIKE '%clockwork%citrus%'
            ORDER BY name
            """
        ).fetchall()
        print(f"  Clockwork Citrus entities: {len(matches):,}")
        for row in matches:
            print(
                "    "
                f"id={row['id']} | type={row['entity_type']} | "
                f"name={row['name']} | slug={row['slug']}"
            )
    return True


def audit(database_path: str | Path = DEFAULT_DATABASE) -> int:
    print()
    print("========================================")
    print(" PHASE 2 PROVISIONING DATA AUDIT")
    print("========================================")

    database_ok = _audit_database(Path(database_path))

    files = _matching_source_files()
    print()
    print(f"Matching local source files: {len(files):,}")
    if not files:
        for directory in SOURCE_DIRECTORIES:
            print(f"  searched: {directory}")
    else:
        for path in files:
            _audit_file(path)

    print()
    if not files:
        print(
            "No local food/drink JSON sources were found. "
            "A canonical provisioning import cannot proceed until source data is supplied."
        )
        return 2 if database_ok else 1
    return 0 if database_ok else 1


if __name__ == "__main__":
    raise SystemExit(audit())
