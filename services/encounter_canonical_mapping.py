from __future__ import annotations

"""Map reviewed encounter evidence into canonical fact shapes without writing DB rows.

This module is intentionally one step before persistence. It translates eligible
promotion candidates, or explicitly reviewed single-source facts, into canonical
semantic kinds and reports whether the current encounter schema can represent the
fact without losing provenance.
"""

from dataclasses import dataclass
from typing import Any, Iterable

from services.encounter_evidence import ReconciledEncounterFact
from services.encounter_promotion import (
    EncounterPromotionCandidate,
    PROMOTION_ELIGIBLE,
)


CANONICAL_MECHANIC_PRESENCE = "mechanic_presence"
CANONICAL_MECHANIC_DETAIL = "mechanic_detail"
CANONICAL_PHASE = "phase"
CANONICAL_PHASE_TRANSITION = "phase_transition"
CANONICAL_STATE = "encounter_state"
CANONICAL_FAILURE_CONDITION = "failure_condition"
CANONICAL_DAMAGE_WINDOW = "damage_window"
CANONICAL_ADD_GROUP = "add_group"
CANONICAL_UNMAPPED = "unmapped"


@dataclass(frozen=True)
class EncounterCanonicalMapping:
    encounter_id: str
    fact_type: str
    fact_key: str
    canonical_kind: str
    payload: dict[str, Any]
    source_count: int
    lossless_in_current_schema: bool
    schema_note: str


def _title_from_key(key: str, *, suffix: str = "") -> str:
    value = key
    if suffix and value.endswith(suffix):
        value = value[: -len(suffix)]
    return value.replace("_", " ").strip().title()


def _v3_note(note: str) -> str:
    return (
        f"{note}; schema v3 preserves each independent source in "
        "encounter_fact_evidence"
    )


def _dict_payload(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {"value": value}


def _map_fact_to_canonical(fact: ReconciledEncounterFact) -> EncounterCanonicalMapping:
    fact_type = fact.fact_type.casefold()
    fact_key = fact.fact_key.casefold()

    if fact_type == "mechanic_state" and fact.value is True:
        suffix = ""
        if fact_key.endswith("_exists"):
            suffix = "_exists"
        elif fact_key.endswith("_exist"):
            suffix = "_exist"

        if suffix:
            name = _title_from_key(fact.fact_key, suffix=suffix)
            return EncounterCanonicalMapping(
                encounter_id=fact.encounter_id,
                fact_type=fact.fact_type,
                fact_key=fact.fact_key,
                canonical_kind=CANONICAL_MECHANIC_PRESENCE,
                payload={"name": name, "present": True},
                source_count=fact.distinct_sources,
                lossless_in_current_schema=True,
                schema_note=_v3_note(
                    "encounter_canonical_fact stores the reviewed mechanic-presence fact"
                ),
            )

    if fact_type == "mechanic_detail":
        return EncounterCanonicalMapping(
            encounter_id=fact.encounter_id,
            fact_type=fact.fact_type,
            fact_key=fact.fact_key,
            canonical_kind=CANONICAL_MECHANIC_DETAIL,
            payload=_dict_payload(fact.value),
            source_count=fact.distinct_sources,
            lossless_in_current_schema=True,
            schema_note=_v3_note(
                "encounter_canonical_fact stores the reviewed mechanic detail without flattening its payload"
            ),
        )

    if fact_type == "failure_condition":
        return EncounterCanonicalMapping(
            encounter_id=fact.encounter_id,
            fact_type=fact.fact_type,
            fact_key=fact.fact_key,
            canonical_kind=CANONICAL_FAILURE_CONDITION,
            payload=_dict_payload(fact.value),
            source_count=fact.distinct_sources,
            lossless_in_current_schema=True,
            schema_note=_v3_note(
                "encounter_canonical_fact stores the reviewed failure condition without flattening its payload"
            ),
        )

    if fact_type == "phase":
        return EncounterCanonicalMapping(
            encounter_id=fact.encounter_id,
            fact_type=fact.fact_type,
            fact_key=fact.fact_key,
            canonical_kind=CANONICAL_PHASE,
            payload=_dict_payload(fact.value),
            source_count=fact.distinct_sources,
            lossless_in_current_schema=True,
            schema_note=_v3_note(
                "encounter_canonical_fact stores the reviewed phase fact"
            ),
        )

    if fact_type == "transition":
        return EncounterCanonicalMapping(
            encounter_id=fact.encounter_id,
            fact_type=fact.fact_type,
            fact_key=fact.fact_key,
            canonical_kind=CANONICAL_PHASE_TRANSITION,
            payload=_dict_payload(fact.value),
            source_count=fact.distinct_sources,
            lossless_in_current_schema=True,
            schema_note=_v3_note(
                "encounter_canonical_fact stores the transition payload without flattening thresholds"
            ),
        )

    if fact_type == "damage_window":
        return EncounterCanonicalMapping(
            encounter_id=fact.encounter_id,
            fact_type=fact.fact_type,
            fact_key=fact.fact_key,
            canonical_kind=CANONICAL_DAMAGE_WINDOW,
            payload=_dict_payload(fact.value),
            source_count=fact.distinct_sources,
            lossless_in_current_schema=True,
            schema_note=_v3_note(
                "encounter_canonical_fact stores the reviewed target-damageability window without collapsing target or phase semantics"
            ),
        )

    if fact_type == "add_group":
        return EncounterCanonicalMapping(
            encounter_id=fact.encounter_id,
            fact_type=fact.fact_type,
            fact_key=fact.fact_key,
            canonical_kind=CANONICAL_ADD_GROUP,
            payload=_dict_payload(fact.value),
            source_count=fact.distinct_sources,
            lossless_in_current_schema=True,
            schema_note=_v3_note(
                "encounter_canonical_fact stores the reviewed add-group payload without inventing unresolved counts or timing"
            ),
        )

    if fact_type in {"phase_state", "transition_state", "response_state"}:
        return EncounterCanonicalMapping(
            encounter_id=fact.encounter_id,
            fact_type=fact.fact_type,
            fact_key=fact.fact_key,
            canonical_kind=CANONICAL_STATE,
            payload={"key": fact.fact_key, "value": fact.value},
            source_count=fact.distinct_sources,
            lossless_in_current_schema=True,
            schema_note=_v3_note(
                "encounter_canonical_fact stores first-class reviewed encounter state"
            ),
        )

    return EncounterCanonicalMapping(
        encounter_id=fact.encounter_id,
        fact_type=fact.fact_type,
        fact_key=fact.fact_key,
        canonical_kind=CANONICAL_UNMAPPED,
        payload={"value": fact.value},
        source_count=fact.distinct_sources,
        lossless_in_current_schema=False,
        schema_note="no reviewed canonical mapping exists for this fact type yet",
    )


def map_reviewed_fact_to_canonical(
    fact: ReconciledEncounterFact,
) -> EncounterCanonicalMapping:
    """Map an explicitly reviewed, non-conflicting fact without changing its status.

    This is the semantic mapping hook for the separate human-review persistence
    path. It does not promote a fact by itself and refuses conflicting evidence.
    Callers remain responsible for proving an explicit review decision exists.
    """

    if not fact.safe_for_review:
        raise ValueError(
            f"encounter fact is not safe for review mapping: "
            f"{fact.encounter_id} :: {fact.fact_type}:{fact.fact_key} :: {fact.status}"
        )
    return _map_fact_to_canonical(fact)


def map_candidate_to_canonical(
    candidate: EncounterPromotionCandidate,
) -> EncounterCanonicalMapping | None:
    """Map one promotion candidate to a canonical semantic shape.

    Only promotion-eligible facts are mapped here. Single-source facts still
    require explicit review through ``map_reviewed_fact_to_canonical`` plus the
    reviewed persistence path. Conflicting facts remain blocked upstream.
    """

    if candidate.promotion_status != PROMOTION_ELIGIBLE:
        return None
    return _map_fact_to_canonical(candidate.fact)


def build_encounter_canonical_mapping_preview(
    candidates: Iterable[EncounterPromotionCandidate],
) -> list[EncounterCanonicalMapping]:
    mappings: list[EncounterCanonicalMapping] = []
    for candidate in candidates:
        mapped = map_candidate_to_canonical(candidate)
        if mapped is not None:
            mappings.append(mapped)
    return mappings
