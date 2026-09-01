from __future__ import annotations

"""Read-only helpers for auditing canonical NPC/entity candidates for encounters."""

from dataclasses import dataclass
import sqlite3
from typing import Iterable


@dataclass(frozen=True)
class NpcCandidate:
    search_name: str
    entity_id: str
    entity_type: str
    entity_name: str
    entity_slug: str
    source: str
    source_entity_type: str
    source_id: str
    source_name: str


@dataclass(frozen=True)
class EncounterNpcAuditRow:
    encounter_id: str
    encounter_name: str
    search_names: tuple[str, ...]
    candidates: tuple[NpcCandidate, ...]
    existing_npc_ids: tuple[str, ...]


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def encounter_search_names(encounter_name: str) -> tuple[str, ...]:
    """Return conservative exact-name candidates for one encounter label.

    Multi-actor labels joined by ' and ' are searched both as a combined label
    and as individual actor names. No fuzzy matching is performed here because
    encounter NPC identity is provenance-sensitive.
    """

    name = " ".join(str(encounter_name).split())
    if not name:
        return ()

    values = [name]
    parts = [part.strip() for part in name.split(" and ") if part.strip()]
    if len(parts) > 1:
        values.extend(parts)

    # Preserve order while removing case-insensitive duplicates.
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)


def _existing_npc_ids(connection: sqlite3.Connection, encounter_id: str) -> tuple[str, ...]:
    if not _table_exists(connection, "encounter_npc"):
        return ()
    rows = connection.execute(
        "SELECT npc_entity_id FROM encounter_npc WHERE encounter_id=? ORDER BY npc_entity_id",
        (encounter_id,),
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _candidates_for_name(connection: sqlite3.Connection, search_name: str) -> tuple[NpcCandidate, ...]:
    if not _table_exists(connection, "entity"):
        return ()

    has_source = _table_exists(connection, "entity_source")
    if has_source:
        rows = connection.execute(
            """
            SELECT
                e.id,
                e.entity_type,
                e.name,
                e.slug,
                COALESCE(es.source, ''),
                COALESCE(es.source_entity_type, ''),
                COALESCE(es.source_id, ''),
                COALESCE(es.source_name, '')
            FROM entity e
            LEFT JOIN entity_source es ON es.entity_id = e.id
            WHERE lower(e.name) = lower(?)
               OR lower(COALESCE(es.source_name, '')) = lower(?)
            ORDER BY e.id, es.source, es.source_entity_type, es.source_id
            """,
            (search_name, search_name),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT id, entity_type, name, slug, '', '', '', ''
            FROM entity
            WHERE lower(name) = lower(?)
            ORDER BY id
            """,
            (search_name,),
        ).fetchall()

    return tuple(
        NpcCandidate(
            search_name=search_name,
            entity_id=str(row[0]),
            entity_type=str(row[1] or ""),
            entity_name=str(row[2] or ""),
            entity_slug=str(row[3] or ""),
            source=str(row[4] or ""),
            source_entity_type=str(row[5] or ""),
            source_id=str(row[6] or ""),
            source_name=str(row[7] or ""),
        )
        for row in rows
    )


def audit_encounter_npc_candidates(
    connection: sqlite3.Connection,
    content_id: str,
) -> list[EncounterNpcAuditRow]:
    if not _table_exists(connection, "encounter"):
        return []

    encounters = connection.execute(
        "SELECT id, name FROM encounter WHERE content_id=? ORDER BY name, id",
        (content_id,),
    ).fetchall()

    result: list[EncounterNpcAuditRow] = []
    for encounter_id, encounter_name in encounters:
        names = encounter_search_names(str(encounter_name))
        candidates: list[NpcCandidate] = []
        seen: set[tuple[str, str, str, str]] = set()
        for search_name in names:
            for candidate in _candidates_for_name(connection, search_name):
                key = (
                    candidate.search_name.casefold(),
                    candidate.entity_id,
                    candidate.source,
                    candidate.source_id,
                )
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(candidate)

        result.append(
            EncounterNpcAuditRow(
                encounter_id=str(encounter_id),
                encounter_name=str(encounter_name),
                search_names=names,
                candidates=tuple(candidates),
                existing_npc_ids=_existing_npc_ids(connection, str(encounter_id)),
            )
        )
    return result
