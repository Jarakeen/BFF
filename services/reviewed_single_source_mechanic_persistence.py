from __future__ import annotations

"""Build canonical persistence plans for human-reviewed single-source mechanics.

This path is deliberately separate from corroboration-based promotion. It accepts
only review-manifest rows explicitly marked accepted and labels resulting facts
``reviewed_single_source``. No second evidence source is invented.
"""

import json
import re
from pathlib import Path
from typing import Iterable

from services.boss_inferred_mechanic_decisions import (
    ACCEPTED,
    InferredMechanicDecision,
)
from services.boss_inferred_mechanic_review import InferredMechanicReviewRow
from services.encounter_canonical_mapping import CANONICAL_MECHANIC_DETAIL
from services.encounter_persistence_plan import (
    EncounterPersistencePlan,
    PlannedCanonicalFactRow,
    PlannedEvidenceRow,
)

REVIEW_STATUS = "reviewed_single_source"
SOURCE_TYPE = "uesp_boss_source"
SOURCE_NAME = "UESP"
SOURCE_FAMILY = "uesp"


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    if not text:
        raise ValueError("mechanic name cannot produce an empty canonical key")
    return text


def _source_payload(row: InferredMechanicReviewRow) -> dict[str, object]:
    """Return only the structured value extracted from the source record."""
    return {
        "name": row.mechanic_name,
        "mechanic_type": row.mechanic_type,
        "damage_type": row.damage_type or None,
        "description": row.description,
        "target_count": row.target_count,
        "requires_movement": row.requires_movement,
        "requires_positioning": row.requires_positioning,
        "requires_cleanse": row.requires_cleanse,
        "persistent_hazard": row.persistent_hazard,
        "failure_is_fatal": row.failure_is_fatal,
        "interruptible": row.interruptible,
    }


def _canonical_payload(
    row: InferredMechanicReviewRow,
    decision: InferredMechanicDecision,
) -> dict[str, object]:
    """Add explicit human-review semantics without rewriting source evidence."""
    payload = _source_payload(row)
    if decision.requirement_subjects:
        payload["requirement_subjects"] = dict(decision.requirement_subjects)
    return payload


def build_reviewed_single_source_plans(
    rows: Iterable[InferredMechanicReviewRow],
    decisions: Iterable[InferredMechanicDecision],
) -> list[EncounterPersistencePlan]:
    """Create lossless plans for accepted single-source mechanic reviews only.

    Every source row must have exactly one matching decision. Pending/rejected
    rows are skipped. Accepted rows require rationale and source provenance.
    Duplicate source or decision keys are refused. Requirement-subject metadata
    is canonical review semantics and is intentionally not copied into the raw
    source-value evidence payload.
    """

    row_by_key: dict[tuple[str, str], InferredMechanicReviewRow] = {}
    for row in rows:
        key = (row.encounter_id, row.mechanic_name)
        if key in row_by_key:
            raise ValueError(f"duplicate inferred mechanic row: {key[0]} :: {key[1]}")
        row_by_key[key] = row

    decision_by_key: dict[tuple[str, str], InferredMechanicDecision] = {}
    for decision in decisions:
        if decision.key in decision_by_key:
            raise ValueError(
                f"duplicate review decision: {decision.encounter_id} :: {decision.mechanic_name}"
            )
        decision_by_key[decision.key] = decision

    missing = sorted(set(row_by_key) - set(decision_by_key))
    extra = sorted(set(decision_by_key) - set(row_by_key))
    if missing:
        encounter_id, mechanic_name = missing[0]
        raise ValueError(f"missing review decision: {encounter_id} :: {mechanic_name}")
    if extra:
        encounter_id, mechanic_name = extra[0]
        raise ValueError(f"review decision has no source row: {encounter_id} :: {mechanic_name}")

    plans: list[EncounterPersistencePlan] = []
    for key in sorted(row_by_key):
        row = row_by_key[key]
        decision = decision_by_key[key]
        if decision.status != ACCEPTED:
            continue
        if not decision.rationale.strip():
            raise ValueError(
                f"accepted review decision has no rationale: {row.encounter_id} :: {row.mechanic_name}"
            )
        if not row.source_url or not row.source_revision:
            raise ValueError(
                f"accepted mechanic is missing UESP provenance: {row.encounter_id} :: {row.mechanic_name}"
            )

        fact_key = _slug(row.mechanic_name)
        logical_ref = f"mechanic_detail:{fact_key}"
        fact = PlannedCanonicalFactRow(
            logical_ref=logical_ref,
            encounter_id=row.encounter_id,
            canonical_kind=CANONICAL_MECHANIC_DETAIL,
            fact_type="mechanic_detail",
            fact_key=fact_key,
            payload_json=_json(_canonical_payload(row, decision)),
            review_status=REVIEW_STATUS,
            valid_from_update="",
            valid_from_patch="",
        )
        subject_note = (
            "\nreview_requirement_subjects="
            + _json(dict(decision.requirement_subjects))
            if decision.requirement_subjects
            else ""
        )
        evidence = PlannedEvidenceRow(
            canonical_fact_ref=logical_ref,
            source_type=SOURCE_TYPE,
            source_name=SOURCE_NAME,
            source_locator=row.source_url,
            source_revision=row.source_revision,
            game_update="",
            patch_version="",
            confidence="reviewed",
            source_value_json=_json(_source_payload(row)),
            notes=(
                f"source_family={SOURCE_FAMILY}\n"
                f"review_status={REVIEW_STATUS}\n"
                f"review_rationale={decision.rationale.strip()}"
                f"{subject_note}"
            ),
        )
        plans.append(EncounterPersistencePlan(fact=fact, evidence=(evidence,)))

    return plans
