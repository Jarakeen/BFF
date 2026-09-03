from __future__ import annotations

from services.encounter_persistence_plan import (
    EncounterPersistencePlan,
    PlannedCanonicalFactRow,
    PlannedEvidenceRow,
)
from services.encounter_persistence_writer import EncounterWriteResult
from tools.write_reviewed_single_source_mechanics import (
    _sum_results,
    group_plans_by_encounter,
)


def _plan(encounter_id: str, key: str) -> EncounterPersistencePlan:
    fact = PlannedCanonicalFactRow(
        logical_ref=f"mechanic_detail:{key}",
        encounter_id=encounter_id,
        canonical_kind="mechanic_detail",
        fact_type="mechanic_detail",
        fact_key=key,
        payload_json="{}",
        review_status="reviewed_single_source",
        valid_from_update="",
        valid_from_patch="",
    )
    evidence = PlannedEvidenceRow(
        canonical_fact_ref=fact.logical_ref,
        source_type="uesp_boss_source",
        source_name="UESP",
        source_locator="https://example.invalid",
        source_revision="1",
        game_update="",
        patch_version="",
        confidence="reviewed",
        source_value_json="{}",
        notes="source_family=uesp",
    )
    return EncounterPersistencePlan(fact=fact, evidence=(evidence,))


def test_group_plans_by_encounter_is_sorted_and_keeps_each_batch_single_encounter() -> None:
    groups = group_plans_by_encounter(
        [_plan("zeta", "one"), _plan("alpha", "two"), _plan("zeta", "three")]
    )

    assert [encounter_id for encounter_id, _ in groups] == ["alpha", "zeta"]
    assert [len(plans) for _, plans in groups] == [1, 2]
    for encounter_id, plans in groups:
        assert {plan.fact.encounter_id for plan in plans} == {encounter_id}


def test_sum_results_accumulates_writer_counts() -> None:
    total = _sum_results(
        [
            EncounterWriteResult(1, 2, 3, 4),
            EncounterWriteResult(5, 6, 7, 8),
        ]
    )

    assert total == EncounterWriteResult(
        facts_inserted=6,
        facts_existing=8,
        evidence_inserted=10,
        evidence_existing=12,
    )
