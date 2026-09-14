from pathlib import Path
import json

import pytest

from services.rotation_tank_observed_lane_assignment_service import (
    RotationTankObservedLaneAssignmentService,
)


def test_reviewed_xalvakka_report_maps_observed_tanks_to_distinct_lanes() -> None:
    assignment = RotationTankObservedLaneAssignmentService().reviewed_for(
        encounter_id="xalvakka",
        report_code="XVMgLdq6GpQ7bhKN",
    )

    assert assignment is not None
    assert assignment.evidence_scope == "single_report_reviewed_observed_lane_assignment"
    assert assignment.taunt_state_effect_id == 38254
    assert assignment.fights == (30, 31, 32, 33, 34)

    boss = assignment.lane("boss_holder")
    adds = assignment.lane("add_handler")
    assert boss is not None
    assert adds is not None
    assert boss.character_name == "Dualtalons"
    assert boss.account_name == "@Cerberuss123"
    assert boss.eso_logs_role == "tank"
    assert boss.role_fights == 5
    assert boss.boss_taunt_events == 358
    assert boss.add_taunt_events == 28
    assert adds.character_name == "Fulcinator"
    assert adds.account_name == "@FulciLives"
    assert adds.eso_logs_role == "tank"
    assert adds.role_fights == 5
    assert adds.boss_taunt_events == 82
    assert adds.add_taunt_events == 210
    assert boss.source_id != adds.source_id


def test_single_report_scope_cannot_be_changed_into_generic_scope(tmp_path: Path) -> None:
    payload = {
        "schema_version": 1,
        "assignments": [
            {
                "encounter_id": "xalvakka",
                "report_code": "report",
                "evidence_scope": "generic_encounter_truth",
                "taunt_state_effect_id": 38254,
                "fights": [1],
                "lanes": [
                    {
                        "lane_id": "boss_holder",
                        "source_id": 1,
                        "character_name": "Tank",
                        "account_name": "@Tank",
                        "actor_type": "DragonKnight",
                        "eso_logs_role": "tank",
                        "role_fights": 1,
                        "boss_taunt_events": 1,
                        "boss_fights": 1,
                        "add_taunt_events": 0,
                        "add_instances": 0,
                        "interpretation": "fixture",
                    }
                ],
                "interpretation": "fixture",
            }
        ],
    }
    path = tmp_path / "reviewed.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="evidence_scope"):
        RotationTankObservedLaneAssignmentService(path)
