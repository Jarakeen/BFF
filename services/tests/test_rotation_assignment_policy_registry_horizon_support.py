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


def _symbolic_row():
    return {
        "kind": "taunt_maintenance_horizon",
        "requirement_id": "xalvakka:tank:boss_taunt",
        "encounter_id": "xalvakka",
        "requirement_type": "taunt",
        "source_skill_name": "Pierce Armor",
        "source": "reviewed raid Tank responsibility",
        "windows": [
            {
                "occurrence_id": "boss_ownership",
                "target_key": "boss",
                "active_start_seconds": 0.0,
                "end_reference": "encounter_end",
                "bar": "front",
            }
        ],
    }


def test_registry_keeps_symbolic_encounter_end_policy_separate_from_numeric_policy(tmp_path):
    service = RotationAssignmentPolicyRegistryService(
        _write(tmp_path, [_symbolic_row()])
    )

    bundle = service.for_encounter("XALVAKKA")

    assert bundle.empty is False
    assert bundle.taunt_maintenance_policies == ()
    assert len(bundle.taunt_maintenance_horizon_policies) == 1
    policy = bundle.taunt_maintenance_horizon_policies[0]
    assert policy.requirement_id == "xalvakka:tank:boss_taunt"
    assert policy.windows[0].end_reference == "encounter_end"
    assert policy.windows[0].active_start_seconds == 0.0


def test_registry_accepts_reviewed_health_threshold_symbolic_endpoint(tmp_path):
    row = _symbolic_row()
    row["windows"][0]["occurrence_id"] = "phase_1_boss_ownership"
    row["windows"][0]["end_reference"] = "health_threshold:70%"

    service = RotationAssignmentPolicyRegistryService(_write(tmp_path, [row]))
    policy = service.for_encounter("xalvakka").taunt_maintenance_horizon_policies[0]

    assert policy.windows[0].end_reference == "health_threshold:70%"


def test_registry_allows_symbolic_policy_to_leave_build_owned_taunt_source_unbound(tmp_path):
    row = _symbolic_row()
    row.pop("source_skill_name")
    row["windows"][0].pop("bar")

    service = RotationAssignmentPolicyRegistryService(_write(tmp_path, [row]))
    policy = service.for_encounter("xalvakka").taunt_maintenance_horizon_policies[0]

    assert policy.source_skill_name is None
    assert policy.windows[0].bar is None


def test_symbolic_policy_still_counts_as_disposition_for_registry_duplicate_guard(tmp_path):
    numeric = {
        "kind": "taunt_maintenance",
        "requirement_id": "xalvakka:tank:boss_taunt",
        "encounter_id": "xalvakka",
        "requirement_type": "taunt",
        "source_skill_name": "Pierce Armor",
        "source": "fixture",
        "windows": [
            {
                "occurrence_id": "boss_ownership",
                "target_key": "boss",
                "active_start_seconds": 0.0,
                "active_end_seconds": 30.0,
            }
        ],
    }

    with pytest.raises(ValueError, match="multiple dispositions"):
        RotationAssignmentPolicyRegistryService(
            _write(tmp_path, [_symbolic_row(), numeric])
        )


def test_registry_rejects_unrecognized_symbolic_end_reference(tmp_path):
    row = _symbolic_row()
    row["windows"][0]["end_reference"] = "probably_when_boss_dies"

    with pytest.raises(ValueError, match="encounter_end"):
        RotationAssignmentPolicyRegistryService(_write(tmp_path, [row]))
