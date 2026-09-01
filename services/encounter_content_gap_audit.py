from __future__ import annotations

"""Read-only content-scoped audit for canonical encounter recovery coverage."""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_promotion import (
    PROMOTION_BLOCKED,
    PROMOTION_ELIGIBLE,
    PROMOTION_REVIEW_REQUIRED,
    build_encounter_promotion_preview,
)
from tools.reconcile_encounter_evidence import _load_packet


@dataclass(frozen=True)
class EncounterPacketGap:
    packet_path: Path
    encounter_id: str
    encounter_name: str
    reconciled_facts: int
    eligible: tuple[str, ...]
    review_required: tuple[str, ...]
    blocked: tuple[str, ...]
    persisted: tuple[str, ...]
    missing_eligible: tuple[str, ...]


@dataclass(frozen=True)
class EncounterDatabaseCoverage:
    encounter_id: str
    name: str
    npc_count: int
    health_count: int
    ability_count: int
    mechanic_count: int
    phase_count: int
    dialogue_count: int
    canonical_fact_count: int
    canonical_evidence_count: int


@dataclass(frozen=True)
class EncounterContentGapAudit:
    content_id: str
    content_name: str
    database_encounters: tuple[EncounterDatabaseCoverage, ...]
    packet_gaps: tuple[EncounterPacketGap, ...]
    encounters_without_packets: tuple[str, ...]
    packets_without_encounters: tuple[str, ...]
    source_declared_encounters: tuple[str, ...]
    source_declared_missing_db: tuple[str, ...]
    source_declared_missing_packets: tuple[str, ...]


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _count_for_encounter(connection: sqlite3.Connection, table: str, encounter_id: str) -> int:
    if not _table_exists(connection, table):
        return 0
    row = connection.execute(
        f'SELECT COUNT(*) FROM "{table}" WHERE encounter_id=?',
        (encounter_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def _canonical_evidence_count(connection: sqlite3.Connection, encounter_id: str) -> int:
    if not _table_exists(connection, "encounter_fact_evidence") or not _table_exists(
        connection, "encounter_canonical_fact"
    ):
        return 0
    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM encounter_fact_evidence efe
        JOIN encounter_canonical_fact ecf ON ecf.id = efe.canonical_fact_id
        WHERE ecf.encounter_id=?
        """,
        (encounter_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def _persisted_refs(connection: sqlite3.Connection, encounter_id: str) -> set[str]:
    if not _table_exists(connection, "encounter_canonical_fact"):
        return set()
    return {
        f"{row[0]}:{row[1]}"
        for row in connection.execute(
            "SELECT fact_type, fact_key FROM encounter_canonical_fact WHERE encounter_id=?",
            (encounter_id,),
        )
    }


def _source_declared_encounters(source_root: Path, content_id: str) -> tuple[str, ...]:
    """Return boss_ids declared by the tracked UESP content record, if present."""

    if not source_root.exists():
        return ()

    for path in sorted(source_root.glob(f"*/{content_id}.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict) or str(payload.get("id", "")).strip() != content_id:
            continue
        boss_ids = payload.get("boss_ids")
        if not isinstance(boss_ids, list):
            return ()
        return tuple(
            sorted(
                {
                    str(encounter_id).strip()
                    for encounter_id in boss_ids
                    if str(encounter_id).strip()
                }
            )
        )
    return ()


def audit_encounter_packet(
    connection: sqlite3.Connection,
    packet_path: Path,
) -> EncounterPacketGap:
    payload, evidence = _load_packet(packet_path)
    facts = reconcile_encounter_evidence(evidence)
    candidates = build_encounter_promotion_preview(facts)

    encounter_id = str(payload.get("encounter_id", "")).strip()
    persisted = _persisted_refs(connection, encounter_id)

    by_status: dict[str, list[str]] = {
        PROMOTION_ELIGIBLE: [],
        PROMOTION_REVIEW_REQUIRED: [],
        PROMOTION_BLOCKED: [],
    }
    for candidate in candidates:
        ref = f"{candidate.fact.fact_type}:{candidate.fact.fact_key}"
        by_status[candidate.promotion_status].append(ref)

    eligible = set(by_status[PROMOTION_ELIGIBLE])
    return EncounterPacketGap(
        packet_path=packet_path,
        encounter_id=encounter_id,
        encounter_name=str(payload.get("encounter_name") or encounter_id),
        reconciled_facts=len(facts),
        eligible=tuple(sorted(eligible)),
        review_required=tuple(sorted(by_status[PROMOTION_REVIEW_REQUIRED])),
        blocked=tuple(sorted(by_status[PROMOTION_BLOCKED])),
        persisted=tuple(sorted(persisted)),
        missing_eligible=tuple(sorted(eligible - persisted)),
    )


def audit_content_encounters(
    connection: sqlite3.Connection,
    *,
    content_id: str,
    packet_dir: Path,
    source_root: Path = Path("data/uesp"),
) -> EncounterContentGapAudit:
    content_row = connection.execute(
        "SELECT name FROM content WHERE id=?",
        (content_id,),
    ).fetchone()
    if content_row is None:
        raise ValueError(f"Canonical content row does not exist: {content_id!r}")

    encounter_rows = connection.execute(
        "SELECT id, name FROM encounter WHERE content_id=? ORDER BY name, id",
        (content_id,),
    ).fetchall()

    database_encounters: list[EncounterDatabaseCoverage] = []
    for encounter_id, name in encounter_rows:
        encounter_id = str(encounter_id)
        database_encounters.append(
            EncounterDatabaseCoverage(
                encounter_id=encounter_id,
                name=str(name),
                npc_count=_count_for_encounter(connection, "encounter_npc", encounter_id),
                health_count=_count_for_encounter(connection, "encounter_health", encounter_id),
                ability_count=_count_for_encounter(connection, "encounter_ability", encounter_id),
                mechanic_count=_count_for_encounter(connection, "encounter_mechanic", encounter_id),
                phase_count=_count_for_encounter(connection, "encounter_phase", encounter_id),
                dialogue_count=_count_for_encounter(connection, "encounter_dialogue", encounter_id),
                canonical_fact_count=_count_for_encounter(
                    connection, "encounter_canonical_fact", encounter_id
                ),
                canonical_evidence_count=_canonical_evidence_count(connection, encounter_id),
            )
        )

    packet_gaps: list[EncounterPacketGap] = []
    for path in sorted(packet_dir.glob("*.json")):
        try:
            payload, _ = _load_packet(path)
        except (OSError, ValueError, KeyError):
            continue
        if str(payload.get("content_id", "")).strip() != content_id:
            continue
        packet_gaps.append(audit_encounter_packet(connection, path))

    encounter_ids = {row.encounter_id for row in database_encounters}
    packet_ids = {row.encounter_id for row in packet_gaps}
    source_ids = set(_source_declared_encounters(source_root, content_id))

    return EncounterContentGapAudit(
        content_id=content_id,
        content_name=str(content_row[0]),
        database_encounters=tuple(database_encounters),
        packet_gaps=tuple(packet_gaps),
        encounters_without_packets=tuple(sorted(encounter_ids - packet_ids)),
        packets_without_encounters=tuple(sorted(packet_ids - encounter_ids)),
        source_declared_encounters=tuple(sorted(source_ids)),
        source_declared_missing_db=tuple(sorted(source_ids - encounter_ids)),
        source_declared_missing_packets=tuple(sorted(source_ids - packet_ids)),
    )
