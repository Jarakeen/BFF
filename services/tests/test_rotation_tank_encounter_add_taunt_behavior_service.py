import json

import pytest

from services.rotation_tank_encounter_add_taunt_behavior_service import (
    RotationTankEncounterAddTauntBehaviorService,
)


def test_reviewed_xalvakka_empirical_taunt_behavior_stays_non_authoritative():
    plan = RotationTankEncounterAddTauntBehaviorService().reviewed_for("xalvakka")

    assert plan is not None
    assert plan.evidence_scope == "single_report_empirical_strategy"
    assert plan.source_report == "XVMgLdq6GpQ7bhKN"
    assert plan.observed_taunt_sources == ("Fulcinator",)

    iron = plan.actor("Iron Atronach")
    daedroth = plan.actor("Daedroth")
    assert iron is not None and daedroth is not None

    assert iron.taunted_instances == 16
    assert iron.observed_instances == 18
    assert iron.acquisition_lag.median_seconds == pytest.approx(4.581)
    assert iron.repeat_taunt_interval.samples == 61
    assert iron.candidate_ranking_context is True
    assert iron.hard_timing_policy is False
    assert iron.continuous_ownership_proven is False

    assert daedroth.taunted_instances == 17
    assert daedroth.observed_instances == 27
    assert daedroth.acquisition_lag.median_seconds == pytest.approx(13.727)
    assert daedroth.repeat_taunt_interval.samples == 18
    assert daedroth.hard_timing_policy is False
    assert daedroth.continuous_ownership_proven is False


def test_service_rejects_single_report_behavior_promoted_to_hard_policy(tmp_path):
    payload = {
        "schema_version": 1,
        "encounters": [
            {
                "encounter_id": "xalvakka",
                "evidence_scope": "single_report_empirical_strategy",
                "source_report": "report",
                "observed_taunt_sources": ["tank"],
                "interpretation": "fixture",
                "actors": [
                    {
                        "actor_name": "Iron Atronach",
                        "observed_instances": 1,
                        "taunted_instances": 1,
                        "untaunted_instances": 0,
                        "acquisition_lag_seconds": {
                            "samples": 1,
                            "median": 1.0,
                            "minimum": 1.0,
                            "maximum": 1.0,
                        },
                        "repeat_taunt_interval_seconds": {
                            "samples": 1,
                            "median": 8.0,
                            "minimum": 8.0,
                            "maximum": 8.0,
                        },
                        "candidate_ranking_context": True,
                        "hard_timing_policy": True,
                        "continuous_ownership_proven": False,
                    }
                ],
            }
        ],
    }
    path = tmp_path / "reviewed.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="cannot be hard timing policy"):
        RotationTankEncounterAddTauntBehaviorService(path)
