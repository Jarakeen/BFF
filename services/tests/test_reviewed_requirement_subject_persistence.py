from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.boss_inferred_mechanic_decisions import (
    ACCEPTED,
    InferredMechanicDecision,
    load_decisions,
)
from services.boss_inferred_mechanic_review import InferredMechanicReviewRow
from services.reviewed_single_source_mechanic_persistence import (
    build_reviewed_single_source_plans,
)


def _row() -> InferredMechanicReviewRow:
    return InferredMechanicReviewRow(
        source_path=Path("hiath.json"),
        content_id="dragonstar_arena",
        encounter_id="hiath_the_battlemaster",
        encounter_name="Hiath the Battlemaster",
        mechanic_name="Roll Dodge",
        mechanic_type="movement",
        damage_type="",
        description="Hiath can perform a roll dodge to avoid incoming damage.",
        target_count=None,
        requires_movement=True,
        requires_positioning=None,
        requires_cleanse=None,
        persistent_hazard=None,
        failure_is_fatal=None,
        interruptible=None,
        source_url="https://en.uesp.net/wiki/Online:Hiath_the_Battlemaster",
        source_revision="123",
        issues=(),
    )


def test_review_manifest_parses_optional_requirement_subjects(tmp_path: Path) -> None:
    manifest = tmp_path / "review.json"
    manifest.write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "encounter_id": "hiath_the_battlemaster",
                        "mechanic_name": "Roll Dodge",
                        "status": "accepted",
                        "rationale": "Hiath is the actor performing the movement.",
                        "requirement_subjects": {"movement": "boss"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    decision = load_decisions(manifest)[0]

    assert decision.requirement_subjects == (("movement", "boss"),)


def test_review_manifest_rejects_invalid_requirement_subject(tmp_path: Path) -> None:
    manifest = tmp_path / "review.json"
    manifest.write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "encounter_id": "hiath_the_battlemaster",
                        "mechanic_name": "Roll Dodge",
                        "status": "accepted",
                        "rationale": "Reviewed.",
                        "requirement_subjects": {"movement": "the vibes"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported requirement subject"):
        load_decisions(manifest)


def test_reviewed_subject_is_canonical_semantics_not_raw_source_value() -> None:
    decision = InferredMechanicDecision(
        encounter_id="hiath_the_battlemaster",
        mechanic_name="Roll Dodge",
        status=ACCEPTED,
        rationale="Hiath is explicitly the actor performing the dodge.",
        requirement_subjects=(("movement", "boss"),),
    )

    plan = build_reviewed_single_source_plans([_row()], [decision])[0]
    canonical = json.loads(plan.fact.payload_json)
    source_value = json.loads(plan.evidence[0].source_value_json)

    assert canonical["requires_movement"] is True
    assert canonical["requirement_subjects"] == {"movement": "boss"}
    assert "requirement_subjects" not in source_value
    assert "review_requirement_subjects={\"movement\":\"boss\"}" in plan.evidence[0].notes


def test_legacy_review_decision_without_subjects_preserves_payload_shape() -> None:
    decision = InferredMechanicDecision(
        encounter_id="hiath_the_battlemaster",
        mechanic_name="Roll Dodge",
        status=ACCEPTED,
        rationale="Reviewed before actor ownership metadata existed.",
    )

    plan = build_reviewed_single_source_plans([_row()], [decision])[0]

    assert "requirement_subjects" not in json.loads(plan.fact.payload_json)
    assert "review_requirement_subjects=" not in plan.evidence[0].notes
