from services.encounter_evidence import EncounterEvidence, reconcile_encounter_evidence
from services.encounter_promotion import (
    PROMOTION_BLOCKED,
    PROMOTION_ELIGIBLE,
    PROMOTION_REVIEW_REQUIRED,
    build_encounter_promotion_preview,
)


def _fact(*rows: EncounterEvidence):
    facts = reconcile_encounter_evidence(rows)
    assert len(facts) == 1
    return facts[0]


def test_corroborated_fact_is_eligible():
    fact = _fact(
        EncounterEvidence(
            encounter_id="boss",
            fact_type="mechanic_state",
            fact_key="wave_exists",
            value=True,
            source_type="uesp",
            source_name="UESP",
        ),
        EncounterEvidence(
            encounter_id="boss",
            fact_type="mechanic_state",
            fact_key="wave_exists",
            value=True,
            source_type="guide",
            source_name="Guide",
        ),
    )
    candidate = build_encounter_promotion_preview([fact])[0]
    assert candidate.promotion_status == PROMOTION_ELIGIBLE


def test_single_source_fact_requires_review():
    fact = _fact(
        EncounterEvidence(
            encounter_id="boss",
            fact_type="transition",
            fact_key="execute",
            value={"threshold": "20%"},
            source_type="guide",
            source_name="Guide",
        )
    )
    candidate = build_encounter_promotion_preview([fact])[0]
    assert candidate.promotion_status == PROMOTION_REVIEW_REQUIRED


def test_conflicting_fact_is_blocked():
    fact = _fact(
        EncounterEvidence(
            encounter_id="boss",
            fact_type="transition",
            fact_key="execute",
            value={"threshold": "20%"},
            source_type="uesp",
            source_name="UESP",
        ),
        EncounterEvidence(
            encounter_id="boss",
            fact_type="transition",
            fact_key="execute",
            value={"threshold": "25%"},
            source_type="guide",
            source_name="Guide",
        ),
    )
    candidate = build_encounter_promotion_preview([fact])[0]
    assert candidate.promotion_status == PROMOTION_BLOCKED
    assert candidate.fact.value is None
