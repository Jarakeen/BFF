from __future__ import annotations

from pathlib import Path

import pytest

from services.boss_inferred_mechanic_decisions import InferredMechanicDecision
from services.boss_inferred_mechanic_review import InferredMechanicReviewRow
from services.reviewed_single_source_mechanic_persistence import (
    REVIEW_STATUS,
    build_reviewed_single_source_plans,
)


def _row(**overrides) -> InferredMechanicReviewRow:
    values = dict(
        source_path=Path("boss.json"),
        content_id="rockgrove",
        encounter_id="oaxiltso",
        encounter_name="Oaxiltso",
        mechanic_name="Noxious Sludge",
        mechanic_type="targeted_hazard",
        damage_type="poison",
        description="Two targets are poisoned and must walk into a cleansing pool.",
        target_count=2,
        requires_movement=True,
        requires_positioning=True,
        requires_cleanse=True,
        persistent_hazard=None,
        failure_is_fatal=None,
        interruptible=None,
        source_url="https://en.uesp.net/wiki/Online:Oaxiltso",
        source_revision="123",
        issues=(),
    )
    values.update(overrides)
    return InferredMechanicReviewRow(**values)


def test_builds_single_source_plan_without_inventing_corroboration() -> None:
    row = _row()
    decision = InferredMechanicDecision(
        encounter_id=row.encounter_id,
        mechanic_name=row.mechanic_name,
        status="accepted",
        rationale="Reviewed against the UESP source description.",
    )

    plans = build_reviewed_single_source_plans([row], [decision])

    assert len(plans) == 1
    plan = plans[0]
    assert plan.fact.review_status == REVIEW_STATUS
    assert plan.fact.fact_type == "mechanic_detail"
    assert plan.fact.fact_key == "noxious_sludge"
    assert len(plan.evidence) == 1
    assert plan.evidence[0].source_name == "UESP"
    assert "review_rationale=Reviewed against the UESP source description." in plan.evidence[0].notes
    assert "corroborated" not in plan.fact.review_status


def test_skips_pending_and_rejected_decisions() -> None:
    rows = [_row(mechanic_name="Pending"), _row(mechanic_name="Rejected")]
    decisions = [
        InferredMechanicDecision("oaxiltso", "Pending", "pending", ""),
        InferredMechanicDecision("oaxiltso", "Rejected", "rejected", "Not source-supported."),
    ]
    assert build_reviewed_single_source_plans(rows, decisions) == []


def test_requires_complete_manifest_alignment() -> None:
    with pytest.raises(ValueError, match="missing review decision"):
        build_reviewed_single_source_plans([_row()], [])


def test_requires_rationale_and_provenance_for_accepted_rows() -> None:
    row = _row()
    with pytest.raises(ValueError, match="no rationale"):
        build_reviewed_single_source_plans(
            [row],
            [InferredMechanicDecision(row.encounter_id, row.mechanic_name, "accepted", "")],
        )

    no_source = _row(source_url="")
    with pytest.raises(ValueError, match="missing UESP provenance"):
        build_reviewed_single_source_plans(
            [no_source],
            [
                InferredMechanicDecision(
                    no_source.encounter_id,
                    no_source.mechanic_name,
                    "accepted",
                    "Reviewed.",
                )
            ],
        )
