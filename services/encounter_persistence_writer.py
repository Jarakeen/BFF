from __future__ import annotations

"""Controlled persistence for reviewed encounter facts.

This module writes only schema-v3 canonical fact/evidence rows. It deliberately
refuses to create content or encounter rows and never guesses around missing
schema or conflicting existing payloads.
"""

from dataclasses import dataclass
import sqlite3
from typing import Iterable

from services.encounter_persistence_plan import EncounterPersistencePlan


REQUIRED_TABLES = {
    "content",
    "encounter",
    "encounter_canonical_fact",
    "encounter_fact_evidence",
}


@dataclass(frozen=True)
class EncounterWriteResult:
    facts_inserted: int = 0
    facts_existing: int = 0
    evidence_inserted: int = 0
    evidence_existing: int = 0


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def _existing_evidence_row(
    connection: sqlite3.Connection,
    canonical_fact_id: int,
    evidence,
):
    return connection.execute(
        """
        SELECT id, confidence, source_value_json, notes
        FROM encounter_fact_evidence
        WHERE canonical_fact_id = ?
          AND source_type = ?
          AND source_name = ?
          AND source_locator = ?
          AND source_revision = ?
          AND game_update = ?
          AND patch_version = ?
        """,
        (
            canonical_fact_id,
            evidence.source_type,
            evidence.source_name,
            evidence.source_locator,
            evidence.source_revision,
            evidence.game_update,
            evidence.patch_version,
        ),
    ).fetchone()


def _validate_existing_evidence(existing, evidence, logical_ref: str) -> None:
    if existing is None:
        return
    actual = (str(existing[1]), str(existing[2]), str(existing[3] or ""))
    expected = (
        evidence.confidence,
        evidence.source_value_json,
        evidence.notes,
    )
    if actual != expected:
        raise RuntimeError(
            "Existing encounter evidence conflicts with reviewed plan: "
            f"{logical_ref} | {evidence.source_type}:{evidence.source_name}"
        )


def validate_persistence_target(
    connection: sqlite3.Connection,
    plans: Iterable[EncounterPersistencePlan],
) -> None:
    plans = list(plans)
    missing = sorted(REQUIRED_TABLES - _table_names(connection))
    if missing:
        raise RuntimeError(
            "Encounter persistence target is missing required table(s): "
            + ", ".join(missing)
        )

    encounter_ids = {plan.fact.encounter_id for plan in plans}
    if len(encounter_ids) > 1:
        raise RuntimeError("A controlled persistence batch must target one encounter")
    if not encounter_ids:
        return

    encounter_id = next(iter(encounter_ids))
    encounter = connection.execute(
        "SELECT content_id FROM encounter WHERE id = ?",
        (encounter_id,),
    ).fetchone()
    if encounter is None:
        raise RuntimeError(
            f"Canonical encounter row does not exist: {encounter_id!r}"
        )

    content_id = encounter[0]
    content = connection.execute(
        "SELECT 1 FROM content WHERE id = ?",
        (content_id,),
    ).fetchone()
    if content is None:
        raise RuntimeError(
            f"Encounter {encounter_id!r} references missing content {content_id!r}"
        )

    for plan in plans:
        existing = connection.execute(
            """
            SELECT id, payload_json, canonical_kind, review_status
            FROM encounter_canonical_fact
            WHERE encounter_id = ?
              AND fact_type = ?
              AND fact_key = ?
              AND valid_from_update = ?
              AND valid_from_patch = ?
            """,
            (
                plan.fact.encounter_id,
                plan.fact.fact_type,
                plan.fact.fact_key,
                plan.fact.valid_from_update,
                plan.fact.valid_from_patch,
            ),
        ).fetchone()
        if existing is None:
            continue
        if (
            existing[1] != plan.fact.payload_json
            or existing[2] != plan.fact.canonical_kind
            or existing[3] != plan.fact.review_status
        ):
            raise RuntimeError(
                "Existing canonical fact conflicts with reviewed plan: "
                f"{plan.fact.logical_ref}"
            )

        canonical_fact_id = int(existing[0])
        for evidence in plan.evidence:
            existing_evidence = _existing_evidence_row(
                connection,
                canonical_fact_id,
                evidence,
            )
            _validate_existing_evidence(
                existing_evidence,
                evidence,
                plan.fact.logical_ref,
            )


def persist_encounter_plans(
    connection: sqlite3.Connection,
    plans: Iterable[EncounterPersistencePlan],
) -> EncounterWriteResult:
    """Persist reviewed plans atomically and idempotently.

    The caller owns the connection. This function starts no nested transaction;
    it validates first, writes rows, and raises on any conflicting existing fact
    or evidence provenance record.
    """

    plans = list(plans)
    validate_persistence_target(connection, plans)

    facts_inserted = 0
    facts_existing = 0
    evidence_inserted = 0
    evidence_existing = 0

    for plan in plans:
        row = connection.execute(
            """
            SELECT id
            FROM encounter_canonical_fact
            WHERE encounter_id = ?
              AND fact_type = ?
              AND fact_key = ?
              AND valid_from_update = ?
              AND valid_from_patch = ?
            """,
            (
                plan.fact.encounter_id,
                plan.fact.fact_type,
                plan.fact.fact_key,
                plan.fact.valid_from_update,
                plan.fact.valid_from_patch,
            ),
        ).fetchone()

        if row is None:
            cursor = connection.execute(
                """
                INSERT INTO encounter_canonical_fact (
                    encounter_id, canonical_kind, fact_type, fact_key,
                    payload_json, review_status,
                    valid_from_update, valid_from_patch
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.fact.encounter_id,
                    plan.fact.canonical_kind,
                    plan.fact.fact_type,
                    plan.fact.fact_key,
                    plan.fact.payload_json,
                    plan.fact.review_status,
                    plan.fact.valid_from_update,
                    plan.fact.valid_from_patch,
                ),
            )
            canonical_fact_id = int(cursor.lastrowid)
            facts_inserted += 1
        else:
            canonical_fact_id = int(row[0])
            facts_existing += 1

        for evidence in plan.evidence:
            existing_evidence = _existing_evidence_row(
                connection,
                canonical_fact_id,
                evidence,
            )
            if existing_evidence is not None:
                _validate_existing_evidence(
                    existing_evidence,
                    evidence,
                    plan.fact.logical_ref,
                )
                evidence_existing += 1
                continue

            connection.execute(
                """
                INSERT INTO encounter_fact_evidence (
                    canonical_fact_id, source_type, source_name,
                    source_locator, source_revision, game_update,
                    patch_version, confidence, source_value_json, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    canonical_fact_id,
                    evidence.source_type,
                    evidence.source_name,
                    evidence.source_locator,
                    evidence.source_revision,
                    evidence.game_update,
                    evidence.patch_version,
                    evidence.confidence,
                    evidence.source_value_json,
                    evidence.notes,
                ),
            )
            evidence_inserted += 1

    return EncounterWriteResult(
        facts_inserted=facts_inserted,
        facts_existing=facts_existing,
        evidence_inserted=evidence_inserted,
        evidence_existing=evidence_existing,
    )
