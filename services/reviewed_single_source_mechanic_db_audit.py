from __future__ import annotations

"""Verify reviewed single-source mechanic plans against persisted schema-v3 rows."""

from dataclasses import dataclass
import sqlite3
from typing import Iterable

from services.encounter_persistence_plan import EncounterPersistencePlan


@dataclass(frozen=True)
class ReviewedSingleSourceDbAudit:
    expected_facts: int
    matched_facts: int
    missing_facts: tuple[str, ...]
    conflicting_facts: tuple[str, ...]
    expected_evidence: int
    matched_evidence: int
    missing_evidence: tuple[str, ...]
    conflicting_evidence: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return bool(
            self.missing_facts
            or self.conflicting_facts
            or self.missing_evidence
            or self.conflicting_evidence
            or self.matched_facts != self.expected_facts
            or self.matched_evidence != self.expected_evidence
        )


def audit_reviewed_single_source_database(
    connection: sqlite3.Connection,
    plans: Iterable[EncounterPersistencePlan],
) -> ReviewedSingleSourceDbAudit:
    plans = list(plans)
    missing_facts: list[str] = []
    conflicting_facts: list[str] = []
    missing_evidence: list[str] = []
    conflicting_evidence: list[str] = []
    matched_facts = 0
    matched_evidence = 0
    expected_evidence = sum(len(plan.evidence) for plan in plans)

    for plan in plans:
        fact = plan.fact
        row = connection.execute(
            """
            SELECT id, canonical_kind, payload_json, review_status
            FROM encounter_canonical_fact
            WHERE encounter_id = ?
              AND fact_type = ?
              AND fact_key = ?
              AND valid_from_update = ?
              AND valid_from_patch = ?
            """,
            (
                fact.encounter_id,
                fact.fact_type,
                fact.fact_key,
                fact.valid_from_update,
                fact.valid_from_patch,
            ),
        ).fetchone()
        if row is None:
            missing_facts.append(f"{fact.encounter_id} :: {fact.logical_ref}")
            continue

        canonical_fact_id = int(row[0])
        actual_fact = (str(row[1]), str(row[2]), str(row[3]))
        expected_fact = (fact.canonical_kind, fact.payload_json, fact.review_status)
        if actual_fact != expected_fact:
            conflicting_facts.append(f"{fact.encounter_id} :: {fact.logical_ref}")
            continue
        matched_facts += 1

        for evidence in plan.evidence:
            evidence_row = connection.execute(
                """
                SELECT confidence, source_value_json, notes
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
            label = (
                f"{fact.encounter_id} :: {fact.logical_ref} :: "
                f"{evidence.source_type}:{evidence.source_name}"
            )
            if evidence_row is None:
                missing_evidence.append(label)
                continue
            actual_evidence = (
                str(evidence_row[0]),
                str(evidence_row[1]),
                str(evidence_row[2] or ""),
            )
            expected_evidence_row = (
                evidence.confidence,
                evidence.source_value_json,
                evidence.notes,
            )
            if actual_evidence != expected_evidence_row:
                conflicting_evidence.append(label)
                continue
            matched_evidence += 1

    return ReviewedSingleSourceDbAudit(
        expected_facts=len(plans),
        matched_facts=matched_facts,
        missing_facts=tuple(missing_facts),
        conflicting_facts=tuple(conflicting_facts),
        expected_evidence=expected_evidence,
        matched_evidence=matched_evidence,
        missing_evidence=tuple(missing_evidence),
        conflicting_evidence=tuple(conflicting_evidence),
    )
