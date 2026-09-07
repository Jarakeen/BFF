from __future__ import annotations

"""Build persistence plans for explicitly reviewed single-source encounter facts.

This path is intentionally separate from corroboration-based promotion. A fact
with only one independent evidence source may become canonical only when there is
an explicit review decision for that exact encounter/fact identity. The review
decision is not evidence and never increases the source count.
"""

from dataclasses import dataclass
import json
from typing import Iterable

from services.encounter_canonical_mapping import map_reviewed_fact_to_canonical
from services.encounter_evidence import ReconciledEncounterFact
from services.encounter_persistence_plan import (
    EncounterPersistencePlan,
    PlannedCanonicalFactRow,
    PlannedEvidenceRow,
)


REVIEW_ACCEPTED = "accepted"
REVIEW_REJECTED = "rejected"
REVIEW_PENDING = "pending"
VALID_REVIEW_STATUS = {REVIEW_ACCEPTED, REVIEW_REJECTED, REVIEW_PENDING}
REVIEW_STATUS = "reviewed_single_source"


@dataclass(frozen=True)
class ReviewedEncounterFactDecision:
    encounter_id: str
    fact_type: str
    fact_key: str
    status: str
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.encounter_id.strip():
            raise ValueError("encounter_id is required")
        if not self.fact_type.strip():
            raise ValueError("fact_type is required")
        if not self.fact_key.strip():
            raise ValueError("fact_key is required")
        if self.status not in VALID_REVIEW_STATUS:
            raise ValueError(
                f"status must be one of {sorted(VALID_REVIEW_STATUS)}; got {self.status!r}"
            )
        if self.status == REVIEW_ACCEPTED and not self.rationale.strip():
            raise ValueError("accepted review decisions require rationale")

    @property
    def key(self) -> tuple[str, str, str]:
        return (
            self.encounter_id.strip(),
            self.fact_type.strip().casefold(),
            self.fact_key.strip().casefold(),
        )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _shared_nonempty(values: Iterable[str]) -> str:
    distinct = {value.strip() for value in values if value and value.strip()}
    return next(iter(distinct)) if len(distinct) == 1 else ""


def _evidence_notes(source_family: str, notes: str, rationale: str) -> str:
    parts: list[str] = []
    family = source_family.strip()
    if family:
        parts.append(f"source_family={family}")
    parts.append(f"review_status={REVIEW_STATUS}")
    parts.append(f"review_rationale={rationale.strip()}")
    if notes.strip():
        parts.append(notes.strip())
    return "\n".join(parts)


def build_reviewed_single_source_fact_plans(
    facts: Iterable[ReconciledEncounterFact],
    decisions: Iterable[ReviewedEncounterFactDecision],
) -> list[EncounterPersistencePlan]:
    """Return exact schema-v3 rows for accepted single-source fact reviews.

    Safety rules:
      * every supplied fact must have exactly one review decision;
      * only ``single_source`` facts are accepted on this path;
      * conflicting/corroborated facts must use their existing promotion paths;
      * accepted decisions require a rationale;
      * review never manufactures or duplicates evidence rows;
      * unmapped facts are refused rather than silently flattened.
    """

    fact_by_key: dict[tuple[str, str, str], ReconciledEncounterFact] = {}
    for fact in facts:
        key = (fact.encounter_id.strip(), fact.fact_type.strip().casefold(), fact.fact_key.strip().casefold())
        if key in fact_by_key:
            raise ValueError(f"duplicate reconciled fact: {key[0]} :: {key[1]}:{key[2]}")
        fact_by_key[key] = fact

    decision_by_key: dict[tuple[str, str, str], ReviewedEncounterFactDecision] = {}
    for decision in decisions:
        if decision.key in decision_by_key:
            raise ValueError(
                f"duplicate review decision: {decision.encounter_id} :: "
                f"{decision.fact_type}:{decision.fact_key}"
            )
        decision_by_key[decision.key] = decision

    missing = sorted(set(fact_by_key) - set(decision_by_key))
    extra = sorted(set(decision_by_key) - set(fact_by_key))
    if missing:
        encounter_id, fact_type, fact_key = missing[0]
        raise ValueError(f"missing review decision: {encounter_id} :: {fact_type}:{fact_key}")
    if extra:
        encounter_id, fact_type, fact_key = extra[0]
        raise ValueError(
            f"review decision has no reconciled fact: {encounter_id} :: {fact_type}:{fact_key}"
        )

    plans: list[EncounterPersistencePlan] = []
    for key in sorted(fact_by_key):
        fact = fact_by_key[key]
        decision = decision_by_key[key]

        if fact.status != "single_source":
            raise ValueError(
                f"reviewed single-source path requires status=single_source: "
                f"{fact.encounter_id} :: {fact.fact_type}:{fact.fact_key} :: {fact.status}"
            )
        if decision.status != REVIEW_ACCEPTED:
            continue

        mapping = map_reviewed_fact_to_canonical(fact)
        if not mapping.lossless_in_current_schema:
            raise ValueError(
                f"accepted reviewed fact has no lossless canonical mapping: "
                f"{fact.encounter_id} :: {fact.fact_type}:{fact.fact_key}"
            )

        logical_ref = f"{fact.fact_type}:{fact.fact_key}"
        valid_from_update = _shared_nonempty(row.game_update for row in fact.evidence)
        valid_from_patch = _shared_nonempty(row.patch_version for row in fact.evidence)
        fact_row = PlannedCanonicalFactRow(
            logical_ref=logical_ref,
            encounter_id=fact.encounter_id,
            canonical_kind=mapping.canonical_kind,
            fact_type=fact.fact_type,
            fact_key=fact.fact_key,
            payload_json=_json(mapping.payload),
            review_status=REVIEW_STATUS,
            valid_from_update=valid_from_update,
            valid_from_patch=valid_from_patch,
        )

        evidence_rows = tuple(
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
                notes=_evidence_notes(
                    row.source_family,
                    row.notes,
                    decision.rationale,
                ),
            )
            for row in fact.evidence
        )
        plans.append(EncounterPersistencePlan(fact=fact_row, evidence=evidence_rows))

    return plans
