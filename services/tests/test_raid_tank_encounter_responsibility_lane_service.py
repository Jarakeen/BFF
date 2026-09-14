import json

import pytest

from services.raid_tank_encounter_responsibility_lane_service import (
    RaidTankEncounterResponsibilityLaneService,
)


def _write(tmp_path, payload):
    path = tmp_path / "reviewed.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_production_xalvakka_plan_separates_boss_holder_and_add_handler():
    plan = RaidTankEncounterResponsibilityLaneService().for_encounter("XALVAKKA")

    assert plan is not None
    assert [lane.lane_id for lane in plan.lanes] == ["boss_holder", "add_handler"]

    boss = plan.lane("boss_holder")
    adds = plan.lane("add_handler")
    assert boss is not None
    assert adds is not None
    assert boss.distinct_from == ("add_handler",)
    assert adds.distinct_from == ("boss_holder",)

    boss_taunt = boss.responsibilities[0]
    assert boss_taunt.responsibility_id == "boss_taunt"
    assert boss_taunt.target_key == "xalvakka"
    assert boss_taunt.action_type == "maintain_taunt"
    assert boss_taunt.required_capability_type == "taunt"

    by_id = {row.responsibility_id: row for row in adds.responsibilities}
    assert set(by_id) == {
        "pack_encounter_adds",
        "iron_atronach_opening_position",
        "daedroth_facing",
    }
    assert by_id["pack_encounter_adds"].required_capability_type == "taunt"
    assert by_id["iron_atronach_opening_position"].action_type == "place_away_then_stack"
    assert by_id["daedroth_facing"].action_type == "face_away_from_group"


def test_unknown_encounter_has_no_reviewed_lane_plan():
    assert RaidTankEncounterResponsibilityLaneService().for_encounter("not_real") is None


def test_distinctness_must_be_symmetric(tmp_path):
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "encounters": [
                {
                    "encounter_id": "xalvakka",
                    "source": "fixture",
                    "lanes": [
                        {
                            "lane_id": "boss_holder",
                            "display_name": "Boss Holder",
                            "distinct_from": ["add_handler"],
                            "responsibilities": [
                                {
                                    "responsibility_id": "boss_taunt",
                                    "target_key": "xalvakka",
                                    "action_type": "maintain_taunt",
                                    "source": "fixture",
                                }
                            ],
                        },
                        {
                            "lane_id": "add_handler",
                            "display_name": "Add Handler",
                            "responsibilities": [
                                {
                                    "responsibility_id": "pack_adds",
                                    "target_key": "adds",
                                    "action_type": "stack",
                                    "source": "fixture",
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="distinctness must be symmetric"):
        RaidTankEncounterResponsibilityLaneService(path)


def test_distinctness_cannot_reference_unknown_lane(tmp_path):
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "encounters": [
                {
                    "encounter_id": "xalvakka",
                    "source": "fixture",
                    "lanes": [
                        {
                            "lane_id": "boss_holder",
                            "display_name": "Boss Holder",
                            "distinct_from": ["ghost_lane"],
                            "responsibilities": [
                                {
                                    "responsibility_id": "boss_taunt",
                                    "target_key": "xalvakka",
                                    "action_type": "maintain_taunt",
                                    "source": "fixture",
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="unknown distinct lane"):
        RaidTankEncounterResponsibilityLaneService(path)
