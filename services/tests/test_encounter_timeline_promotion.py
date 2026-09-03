from __future__ import annotations

from services.encounter_evidence import EncounterEvidence
from services.encounter_persistence_writer import EncounterWriteResult
from tools.write_encounter_timeline_facts import _sum_results, _timeline_facts


def _row(*, fact_type: str, fact_key: str, value, source: str) -> EncounterEvidence:
    return EncounterEvidence(
        encounter_id="boss",
        fact_type=fact_type,
        fact_key=fact_key,
        value=value,
        source_type="guide",
        source_name=source,
        confidence="high",
    )


def test_timeline_promotion_filter_keeps_only_phase_and_transition_facts() -> None:
    rows = [
        _row(fact_type="phase", fact_key="phase_2", value={"name": "Phase 2"}, source="A"),
        _row(
            fact_type="transition",
            fact_key="retreat_thresholds",
            value={"thresholds": ["70%", "40%"]},
            source="A",
        ),
        _row(
            fact_type="mechanic_detail",
            fact_key="movement",
            value={"requires_movement": True},
            source="A",
        ),
    ]

    facts = _timeline_facts(rows)

    assert [(row.fact_type, row.fact_key) for row in facts] == [
        ("phase", "phase_2"),
        ("transition", "retreat_thresholds"),
    ]


def test_timeline_filter_preserves_reconciliation_status_for_promotion_policy() -> None:
    rows = [
        _row(
            fact_type="transition",
            fact_key="agreed",
            value={"thresholds": ["50%"]},
            source="A",
        ),
        _row(
            fact_type="transition",
            fact_key="agreed",
            value={"thresholds": ["50%"]},
            source="B",
        ),
        _row(
            fact_type="transition",
            fact_key="conflict",
            value={"thresholds": ["90%"]},
            source="A",
        ),
        _row(
            fact_type="transition",
            fact_key="conflict",
            value={"thresholds": ["95%"]},
            source="B",
        ),
    ]

    facts = {row.fact_key: row for row in _timeline_facts(rows)}

    assert facts["agreed"].status == "corroborated"
    assert facts["agreed"].value == {"thresholds": ["50%"]}
    assert facts["conflict"].status == "conflicting"
    assert facts["conflict"].value is None


def test_sum_results_combines_atomic_writer_counts() -> None:
    result = _sum_results(
        [
            EncounterWriteResult(1, 2, 3, 4),
            EncounterWriteResult(5, 6, 7, 8),
        ]
    )

    assert result == EncounterWriteResult(6, 8, 10, 12)
