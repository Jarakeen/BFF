import json

import pytest

from services.rotation_assignment_policy_registry_service import (
    RotationAssignmentPolicyRegistryService,
)


def _write(tmp_path, policies):
    path = tmp_path / "reviewed.json"
    path.write_text(
        json.dumps({"schema_version": 1, "policies": policies}),
        encoding="utf-8",
    )
    return path


def test_registry_loads_all_reviewed_policy_dispositions(tmp_path):
    service = RotationAssignmentPolicyRegistryService(
        _write(
            tmp_path,
            [
                {
                    "kind": "effect",
                    "requirement_id": "major_berserk",
                    "encounter_id": "taleria_hm",
                    "requirement_type": "major_berserk",
                    "effect_name": "major_berserk",
                    "source_skill_name": "Example Skill",
                    "minimum_uptime": 0.95,
                    "source": "reviewed fixture",
                    "bar": "front",
                },
                {
                    "kind": "taunt",
                    "requirement_id": "boss_taunt",
                    "encounter_id": "taleria_hm",
                    "requirement_type": "boss_taunt",
                    "source_skill_name": "Pierce Armor",
                    "source": "reviewed fixture",
                    "windows": [
                        {
                            "occurrence_id": "pull",
                            "window_start_seconds": 0.0,
                            "window_end_seconds": 1.0,
                            "minimum_applications": 1,
                            "bar": "front",
                            "target_key": "boss",
                        }
                    ],
                },
                {
                    "kind": "taunt_maintenance",
                    "requirement_id": "boss_ownership",
                    "encounter_id": "taleria_hm",
                    "requirement_type": "boss_ownership",
                    "source_skill_name": "Pierce Armor",
                    "source": "reviewed fixture",
                    "windows": [
                        {
                            "occurrence_id": "phase_1",
                            "target_key": "boss",
                            "active_start_seconds": 0.0,
                            "active_end_seconds": 30.0,
                            "bar": "front",
                        }
                    ],
                },
                {
                    "kind": "non_effect",
                    "requirement_id": "position_boss",
                    "encounter_id": "taleria_hm",
                    "requirement_type": "positioning",
                    "reason": "owned by positioning model",
                    "source": "reviewed fixture",
                },
            ],
        )
    )

    bundle = service.for_encounter("TALERIA_HM")

    assert bundle.encounter_id == "taleria_hm"
    assert len(bundle.effect_policies) == 1
    assert bundle.effect_policies[0].minimum_uptime == 0.95
    assert bundle.effect_policies[0].bar == "front"
    assert len(bundle.taunt_policies) == 1
    assert bundle.taunt_policies[0].windows[0].target_key == "boss"
    assert len(bundle.taunt_maintenance_policies) == 1
    assert bundle.taunt_maintenance_policies[0].windows[0].active_end_seconds == 30.0
    assert len(bundle.non_effect_policies) == 1
    assert bundle.non_effect_policies[0].reason == "owned by positioning model"


def test_registry_returns_empty_bundle_for_unreviewed_encounter(tmp_path):
    service = RotationAssignmentPolicyRegistryService(_write(tmp_path, []))

    bundle = service.for_encounter("xalvakka_hm")

    assert bundle.encounter_id == "xalvakka_hm"
    assert bundle.empty is True


def test_registry_rejects_multiple_dispositions_for_same_encounter_requirement(tmp_path):
    path = _write(
        tmp_path,
        [
            {
                "kind": "non_effect",
                "requirement_id": "boss_taunt",
                "encounter_id": "taleria_hm",
                "requirement_type": "boss_taunt",
                "reason": "fixture",
                "source": "fixture",
            },
            {
                "kind": "taunt",
                "requirement_id": "boss_taunt",
                "encounter_id": "taleria_hm",
                "requirement_type": "boss_taunt",
                "source_skill_name": "Pierce Armor",
                "source": "fixture",
                "windows": [
                    {
                        "occurrence_id": "pull",
                        "window_start_seconds": 0.0,
                        "window_end_seconds": 1.0,
                    }
                ],
            },
        ],
    )

    with pytest.raises(ValueError, match="cannot give one requirement multiple dispositions"):
        RotationAssignmentPolicyRegistryService(path)


def test_registry_rejects_unknown_policy_kind(tmp_path):
    path = _write(
        tmp_path,
        [
            {
                "kind": "role_label_guess",
                "requirement_id": "boss_taunt",
                "encounter_id": "taleria_hm",
            }
        ],
    )

    with pytest.raises(ValueError, match="unsupported rotation assignment policy kind"):
        RotationAssignmentPolicyRegistryService(path)
