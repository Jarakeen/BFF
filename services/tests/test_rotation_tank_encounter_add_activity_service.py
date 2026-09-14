import json

import pytest

from services.rotation_tank_encounter_add_activity_service import (
    RotationTankEncounterAddActivityService,
)


def test_reviewed_xalvakka_add_activity_boundary_is_source_backed_and_not_spawn_claim():
    plan = RotationTankEncounterAddActivityService().reviewed_for("xalvakka")

    assert plan is not None
    iron = plan.actor("Iron Atronach")
    daedroth = plan.actor("Daedroth")
    assert iron is not None and daedroth is not None
    assert iron.fully_observed_source_boundary is True
    assert daedroth.fully_observed_source_boundary is True
    assert iron.activity_boundary == "earliest_source_or_involving_event"
    assert daedroth.activity_boundary == "earliest_source_or_involving_event"
    assert "exact spawn" in iron.interpretation
    assert "fixed recurrence timer" in daedroth.interpretation


def test_reviewed_add_activity_rejects_partial_source_coverage(tmp_path):
    path = tmp_path / "reviewed.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "encounters": [
                    {
                        "encounter_id": "x",
                        "source": "reviewed",
                        "actors": [
                            {
                                "actor_name": "Add",
                                "activity_boundary": "earliest_source_or_involving_event",
                                "observed_instances": 2,
                                "signal_coverage": {"involving": 2, "source": 3, "cast": 0},
                                "interpretation": "observed only",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="source_coverage"):
        RotationTankEncounterAddActivityService(path)
