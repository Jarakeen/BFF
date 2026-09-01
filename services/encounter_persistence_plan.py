from __future__ import annotations

"""Build schema-v3 persistence plans for reviewed encounter facts without writing SQLite."""

from dataclasses import dataclass
import json
from typing import Iterable

from services.encounter_canonical_mapping import map_candidate_to_canonical
from services.encounter_promotion import EncounterPromotionCandidate, PROMOTION_ELIGIBLE


@dataclass(frozen=True)
class PlannedCanonicalFactRow:
    logical_ref: str
    encounter_id: str
    canonical_kind: str
    fact_type: str
    fact_key: str
    payload_json: str
    review_status: str
    valid_from_update: str
    valid_from_patch: str


@dataclass(frozen=True)
class PlannedEvidenceRow:
    canonical_fact_ref: str
    source_type: str
    source_name: str
    source_locator: str
    source_revision: str
    game_update: str
    patch_version: str
    confidence: str
    source_value_json: str
    notes: str


@dataclass(frozen=True)
class EncounterPersistencePlan:
    fact: PlannedCanonicalFactRow
    evidence: tuple[PlannedEvidenceRow, ...]


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _shared_nonempty(values: Iterable[str]) -> str:
    distinct = {value.strip() for value in values if value and value.strip()}
    return next(iter(distinct)) if len(distinct) == 1 else ""


def _provenance_notes(source_family: str, notes: str) -> str:
    """Preserve reconciliation lineage inside schema-v3 evidence notes.

    Schema v3 predates source-family reconciliation. Encoding the family as a
    stable first line preserves the relationship without requiring a schema
    migration merely for this metadata field.
    """
    family = source_family.strip()
    body = notes.strip()
    if not family:
        return body
    marker = f"source_family={family}"
    return f"{marker}\n{body}" if body else marker


def build_persistence_plan(
    candidates: Iterable[EncounterPromotionCandidate],
) -> list[EncounterPersistencePlan]:
    """Return exact logical rows that schema v3 could persist.

    Only corroborated/promotion-eligible facts with a reviewed canonical mapping
    are included. The returned plan has no database IDs and performs no writes.
    """

    plans: list[EncounterPersistencePlan] = []

    for candidate in candidates:
        if candidate.promotion_status != PROMOTION_ELIGIBLE:
            continue

        mapping = map_candidate_to_canonical(candidate)
        if mapping is None or not mapping.lossless_in_current_schema:
            continue

        evidence_rows = candidate.fact.evidence
        logical_ref = f"{candidate.fact.fact_type}:{candidate.fact.fact_key}"
        valid_from_update = _shared_nonempty(row.game_update for row in evidence_rows)
        valid_from_patch = _shared_nonempty(row.patch_version for row in evidence_rows)

        fact_row = PlannedCanonicalFactRow(
            logical_ref=logical_ref,
            encounter_id=mapping.encounter_id,
            canonical_kind=mapping.canonical_kind,
            fact_type=mapping.fact_type,
            fact_key=mapping.fact_key,
            payload_json=_json(mapping.payload),
            review_status="reviewed_corroborated",
            valid_from_update=valid_from_update,
            valid_from_patch=valid_from_patch,
        )

        planned_evidence = tuple(
            PlannedEvidenceRow(
                canonical_fact_ref=logical_ref,
                source_type=row.source_type,
                source_name=row.source_name,
                source_locator=row.source_locator,
                source_revision=row.source_revision,
                game_update=row.game_update,
                patch_version=row.patch_version,
                confidence=row.confidence,
                source_value_json=_json(row.value),
                notes=_provenance_notes(row.source_family, row.notes),
            )
            for row in evidence_rows
        )

        plans.append(EncounterPersistencePlan(fact=fact_row, evidence=planned_evidence))

    return plans
