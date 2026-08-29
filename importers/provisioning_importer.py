from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPECTED_ITEM_TYPES = {
    "food": "4",
    "drink": "12",
}


def provisioning_entity_id(kind: str, name: str) -> str:
    """Return a stable text identity while leaving item IDs in the crosswalk."""

    normalized = unicodedata.normalize("NFKD", str(name or ""))
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    normalized = normalized.replace("’", "'")
    normalized = re.sub(r"['`]", "", normalized)
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized)
    slug = re.sub(r"_+", "_", normalized).strip("_").lower()
    return f"{kind}_{slug}" if slug else ""


@dataclass(frozen=True)
class ProvisioningImportSummary:
    source_records: int
    entities_created: int
    entities_existing: int
    mappings_inserted: int
    mappings_updated: int
    unresolved: tuple[str, ...]


class UespProvisioningImporter:
    """Import UESP minedItemSummary food/drink exports into canonical entities."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def load_export(path: str | Path) -> list[dict[str, Any]]:
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected an object in {source}")
        records = payload.get("minedItemSummary")
        if not isinstance(records, list):
            raise ValueError(
                f"Expected a minedItemSummary list in {source}"
            )
        objects = [record for record in records if isinstance(record, dict)]
        declared = payload.get("numRecords")
        if declared not in (None, "") and int(declared) != len(records):
            raise ValueError(
                f"numRecords={declared} does not match "
                f"minedItemSummary={len(records)} in {source}"
            )
        if len(objects) != len(records):
            raise ValueError(f"Non-object records found in {source}")
        return objects

    @staticmethod
    def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
        return {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({table})")
        }

    @classmethod
    def _validate_schema(cls, connection: sqlite3.Connection) -> None:
        required = {
            "entity": {"id", "entity_type", "name", "slug"},
            "entity_source": {
                "id",
                "entity_id",
                "source",
                "source_entity_type",
                "source_id",
                "source_name",
                "raw_json",
            },
        }
        for table, columns in required.items():
            missing = columns - cls._columns(connection, table)
            if missing:
                raise RuntimeError(
                    f"{table} is missing columns: {', '.join(sorted(missing))}"
                )

    @staticmethod
    def _resolve_entity(
        connection: sqlite3.Connection,
        *,
        entity_id: str,
        kind: str,
        name: str,
        slug: str,
    ) -> tuple[str, bool]:
        row = connection.execute(
            """
            SELECT id, entity_type
            FROM entity
            WHERE entity_type = ? AND slug = ?
            """,
            (kind, slug),
        ).fetchone()
        if row is not None:
            return str(row["id"]), False

        collision = connection.execute(
            "SELECT entity_type FROM entity WHERE id = ?",
            (entity_id,),
        ).fetchone()
        if collision is not None:
            raise RuntimeError(
                f"Canonical ID {entity_id!r} already exists as "
                f"{collision['entity_type']!r}"
            )

        connection.execute(
            """
            INSERT INTO entity (id, entity_type, name, slug)
            VALUES (?, ?, ?, ?)
            """,
            (entity_id, kind, name, slug),
        )
        return entity_id, True

    def run(
        self,
        *,
        food_path: str | Path,
        drink_path: str | Path,
    ) -> ProvisioningImportSummary:
        sources = (
            ("food", Path(food_path), self.load_export(food_path)),
            ("drink", Path(drink_path), self.load_export(drink_path)),
        )
        unresolved: list[str] = []
        entities_created = 0
        entities_existing = 0
        mappings_inserted = 0
        mappings_updated = 0

        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            self._validate_schema(connection)

            for kind, source_path, records in sources:
                expected_type = EXPECTED_ITEM_TYPES[kind]
                ordered = sorted(
                    records,
                    key=lambda record: (
                        str(record.get("name") or "").casefold(),
                        int(record.get("itemId") or 0),
                    ),
                )
                for record in ordered:
                    name = str(record.get("name") or "").strip()
                    item_id = str(record.get("itemId") or "").strip()
                    item_type = str(record.get("type") or "").strip()
                    if not name or not item_id:
                        unresolved.append(
                            f"{source_path.name}: record lacks name or itemId"
                        )
                        continue
                    if item_type != expected_type:
                        unresolved.append(
                            f"{source_path.name}: {name} ({item_id}) has "
                            f"type {item_type or '(missing)'}, expected {expected_type}"
                        )
                        continue

                    entity_id = provisioning_entity_id(kind, name)
                    slug = entity_id[len(kind) + 1 :]
                    resolved_id, created = self._resolve_entity(
                        connection,
                        entity_id=entity_id,
                        kind=kind,
                        name=name,
                        slug=slug,
                    )
                    if created:
                        entities_created += 1
                    else:
                        entities_existing += 1

                    existing = connection.execute(
                        """
                        SELECT id
                        FROM entity_source
                        WHERE entity_id = ?
                          AND source = 'UESP'
                          AND source_entity_type = ?
                          AND source_id = ?
                        """,
                        (resolved_id, kind, item_id),
                    ).fetchone()
                    raw_json = json.dumps(record, ensure_ascii=False)
                    if existing is None:
                        connection.execute(
                            """
                            INSERT INTO entity_source (
                                entity_id, source, source_entity_type,
                                source_id, source_name, raw_json
                            )
                            VALUES (?, 'UESP', ?, ?, ?, ?)
                            """,
                            (resolved_id, kind, item_id, name, raw_json),
                        )
                        mappings_inserted += 1
                    else:
                        connection.execute(
                            """
                            UPDATE entity_source
                            SET source_name = ?, raw_json = ?
                            WHERE id = ?
                            """,
                            (name, raw_json, int(existing["id"])),
                        )
                        mappings_updated += 1

                    if not str(record.get("abilityDesc") or "").strip():
                        unresolved.append(
                            f"{kind} {name} ({item_id}) has no abilityDesc"
                        )

            connection.commit()

        return ProvisioningImportSummary(
            source_records=sum(len(records) for _, _, records in sources),
            entities_created=entities_created,
            entities_existing=entities_existing,
            mappings_inserted=mappings_inserted,
            mappings_updated=mappings_updated,
            unresolved=tuple(unresolved),
        )
