from __future__ import annotations

import json

import pytest

from services.encounter_evidence import EncounterEvidence, reconcile_encounter_evidence
from services.reviewed_encounter_fact_persistence import (
    REVIEW_ACCEPTED,
    REVIEW_PENDING,
    REVIEW_REJECTED,
    REVIEW_STATUS,
    ReviewedEncounterFactDecision,
    build_reviewed_single_source_fact_plans,
)


def _fact(fact_type: str, fact_key: str, value):
    rows = [
        EncounterEvidence(
            encounter_id="lokkestiiz",
            fact_type=fact_type,
            fact_key=fact_key,
            value=value,
            source_type="uesp",
            source_name="UESP Online:Lokkestiiz",
            source_locator="Skills and Abilities - Aerial Onslaught",
            source_revision="3606420",
            confidence="high",
            notes="source-backed Lokke flight evidence",
        )
    ]
    return reconcile_encounter_evidence(rows)[0]


def _decision(fact_type: str, fact_key: str, *, status: str = REVIEW_ACCEPTED):
    return ReviewedEncounterFactDecision(
        encounter_id="lokkestiiz",
        fact_type=fact_type,
        fact_key=fact_key,
        status=status,
        rationale="Reviewed source-backed Lokke flight semantics; preserve unresolved details.",
    )


def test_builds_reviewed_single_source_damage_window_without_inventing_corroboration():
    fact = _fact(
        "damage_window",
        "aerial_onslaught_flight",
        {
            "trigger_health_percent": [80, 50, 20],
            "boss_targetable": False,
            "boss_damageable": False,
            "state": "boss_airborne",
            "adds_active": True,
            "raid_damage_active": True,
        },
    )

    plans = build_reviewed_single_source_fact_plans(
        [fact],
        [_decision("damage_window", "aerial_onslaught_flight")],
    )

    assert len(plans) == 1
    plan = plans[0]
    assert plan.fact.canonical_kind == "damage_window"
    assert plan.fact.review_status == REVIEW_STATUS
    assert json.loads(plan.fact.payload_json)["boss_damageable"] is False
    assert len(plan.evidence) == 1
    assert plan.evidence[0].source_name == "UESP Online:Lokkestiiz"
    assert "review_status=reviewed_single_source" in plan.evidence[0].notes
    assert "review_rationale=" in plan.evidence[0].notes


def test_builds_reviewed_add_group_and_preserves_unresolved_count():
    fact = _fact(
        "add_group",
        "aerial_onslaught_atronachs",
        {
            "members": ["Frost Atronach", "Storm Atronach"],
            "trigger": "aerial_onslaught_flight",
            "exact_count_resolved": False,
        },
    )

    plans = build_reviewed_single_source_fact_plans(
        [fact],
        [_decision("add_group", "aerial_onslaught_atronachs")],
    )

    payload = json.loads(plans[0].fact.payload_json)
    assert plans[0].fact.canonical_kind == "add_group"
    assert payload["members"] == ["Frost Atronach", "Storm Atronach"]
    assert payload["exact_count_resolved"] is False
    assert len(plans[0].evidence) == 1


@pytest.mark.parametrize("status", [REVIEW_PENDING, REVIEW_REJECTED])
def test_nonaccepted_reviews_do_not_create_persistence_plans(status):
    fact = _fact("damage_window", "aerial_onslaught_flight", {"boss_damageable": False})
    decision = ReviewedEncounterFactDecision(
        encounter_id="lokkestiiz",
        fact_type="damage_window",
        fact_key="aerial_onslaught_flight",
        status=status,
        rationale="not accepted yet",
    )

    assert build_reviewed_single_source_fact_plans([fact], [decision]) == []


def test_missing_review_decision_is_refused():
    fact = _fact("damage_window", "aerial_onslaught_flight", {"boss_damageable": False})

    with pytest.raises(ValueError, match="missing review decision"):
        build_reviewed_single_source_fact_plans([fact], [])


def test_review_decision_without_matching_fact_is_refused():
    fact = _fact("damage_window", "aerial_onslaught_flight", {"boss_damageable": False})

    with pytest.raises(ValueError, match="review decision has no reconciled fact"):
        build_reviewed_single_source_fact_plans(
            [fact],
            [
                _decision("damage_window", "aerial_onslaught_flight"),
                _decision("add_group", "aerial_onslaught_atronachs"),
            ],
        )


def test_corroborated_fact_must_use_normal_promotion_path():
    rows = [
        EncounterEvidence(
            encounter_id="lokkestiiz",
            fact_type="damage_window",
            fact_key="aerial_onslaught_flight",
            value={"boss_damageable": False},
            source_type="uesp",
            source_name="UESP",
        ),
        EncounterEvidence(
            encounter_id="lokkestiiz",
            fact_type="damage_window",
            fact_key="aerial_onslaught_flight",
            value={"boss_damageable": False},
            source_type="guide",
            source_name="Independent Guide",
        ),
    ]
    fact = reconcile_encounter_evidence(rows)[0]

    with pytest.raises(ValueError, match="requires status=single_source"):
        build_reviewed_single_source_fact_plans(
            [fact],
            [_decision("damage_window", "aerial_onslaught_flight")],
        )


def test_unmapped_accepted_fact_is_refused_instead_of_flattened():
    fact = _fact("mystery_fact", "unknown_shape", {"something": True})

    with pytest.raises(ValueError, match="no lossless canonical mapping"):
        build_reviewed_single_source_fact_plans(
            [fact],
            [_decision("mystery_fact", "unknown_shape")],
        )


def test_accepted_review_requires_rationale():
    with pytest.raises(ValueError, match="require rationale"):
        ReviewedEncounterFactDecision(
            encounter_id="lokkestiiz",
            fact_type="damage_window",
            fact_key="aerial_onslaught_flight",
            status=REVIEW_ACCEPTED,
            rationale="",
        )
