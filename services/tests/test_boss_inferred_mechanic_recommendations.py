from __future__ import annotations

import json
from pathlib import Path

from services.boss_inferred_mechanic_recommendations import (
    build_recommendations,
    recommend_mechanic,
)
from services.boss_inferred_mechanic_review import InferredMechanicReviewRow


def _row(**overrides) -> InferredMechanicReviewRow:
    values = dict(
        source_path=Path("boss.json"),
        content_id="rockgrove",
        encounter_id="oaxiltso",
        encounter_name="Oaxiltso",
        mechanic_name="Noxious Sludge",
        mechanic_type="targeted_hazard",
        damage_type="poison",
        description="Two targets are poisoned and must walk into a cleansing pool; poison pools remain on the ground.",
        target_count=2,
        requires_movement=True,
        requires_positioning=None,
        requires_cleanse=True,
        persistent_hazard=True,
        failure_is_fatal=None,
        interruptible=None,
        source_url="https://example.invalid",
        source_revision="1",
        issues=(),
    )
    values.update(overrides)
    return InferredMechanicReviewRow(**values)


def test_recommend_accepts_only_fully_explicit_fields() -> None:
    recommendation = recommend_mechanic(_row())
    assert recommendation.recommended_status == "accepted"
    assert all(item.status == "supported" for item in recommendation.field_support)


def test_recommend_keeps_unclear_field_pending() -> None:
    recommendation = recommend_mechanic(
        _row(description="Two targets are poisoned and must walk into a cleansing pool.", persistent_hazard=True)
    )
    assert recommendation.recommended_status == "pending"
    assert any(item.field == "persistent_hazard" and item.status != "supported" for item in recommendation.field_support)


def test_build_recommendations_filters_to_requested_content_type(tmp_path: Path) -> None:
    root = tmp_path / "eso_info"
    bosses = root / "bosses"
    trials = root / "trials"
    dungeons = root / "dungeons"
    bosses.mkdir(parents=True)
    trials.mkdir()
    dungeons.mkdir()

    (trials / "rockgrove.json").write_text(json.dumps({"id": "rockgrove"}), encoding="utf-8")
    (dungeons / "other.json").write_text(json.dumps({"id": "other"}), encoding="utf-8")

    payload = {
        "id": "oaxiltso",
        "name": "Oaxiltso",
        "content_id": "rockgrove",
        "source": {"url": "https://example.invalid", "revision_id": 1},
        "mechanics": [
            {
                "name": "Fiery Stomp",
                "description": "A flame area attack erupts around the boss.",
                "mechanic_type": "area_attack",
                "damage_type": "flame",
                "interpretation_status": "inferred",
            }
        ],
    }
    (bosses / "oaxiltso.json").write_text(json.dumps(payload), encoding="utf-8")

    recommendations = build_recommendations(bosses, root, content_type="trial")
    assert len(recommendations) == 1
    assert recommendations[0].row.encounter_id == "oaxiltso"
