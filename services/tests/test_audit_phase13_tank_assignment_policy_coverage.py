import json

from services.rotation_assignment_policy_registry_service import (
    RotationAssignmentPolicyRegistryService,
)
from tools.audit_phase13_tank_assignment_policy_coverage import audit_encounter


def _registry(tmp_path, policies):
    path = tmp_path / "reviewed.json"
    path.write_text(
        json.dumps({"schema_version": 1, "policies": policies}),
        encoding="utf-8",
    )
    return RotationAssignmentPolicyRegistryService(path)


def test_audit_requires_exact_canonical_tank_requirement_identity(tmp_path):
    registry = _registry(
        tmp_path,
        [
            {
                "kind": "taunt",
                "requirement_id": "boss_taunt",
                "encounter_id": "xalvakka",
                "requirement_type": "taunt",
                "source_skill_name": "Pierce Armor",
                "source": "fixture using deliberately shortened identity",
                "windows": [
                    {
                        "occurrence_id": "pull",
                        "window_start_seconds": 0.0,
                        "window_end_seconds": 1.0,
                    }
                ],
            }
        ],
    )

    rows = audit_encounter("xalvakka", registry=registry)

    assert len(rows) == 1
    assert rows[0].requirement_id == "xalvakka:tank:boss_taunt"
    assert rows[0].disposition == "missing"
    assert rows[0].reviewed is False


def test_audit_recognizes_exact_reviewed_tank_requirement_identity(tmp_path):
    registry = _registry(
        tmp_path,
        [
            {
                "kind": "taunt",
                "requirement_id": "xalvakka:tank:boss_taunt",
                "encounter_id": "xalvakka",
                "requirement_type": "taunt",
                "source_skill_name": "Pierce Armor",
                "source": "reviewed fixture",
                "windows": [
                    {
                        "occurrence_id": "pull",
                        "window_start_seconds": 0.0,
                        "window_end_seconds": 1.0,
                    }
                ],
            }
        ],
    )

    rows = audit_encounter("xalvakka", registry=registry)

    assert len(rows) == 1
    assert rows[0].disposition == "taunt"
    assert rows[0].reviewed is True
    assert rows[0].executable_before_horizon_materialization is True
    assert rows[0].source == "reviewed fixture"


def test_audit_marks_symbolic_horizon_policy_as_reviewed_but_not_yet_executable(tmp_path):
    registry = _registry(
        tmp_path,
        [
            {
                "kind": "taunt_maintenance_horizon",
                "requirement_id": "xalvakka:tank:boss_taunt",
                "encounter_id": "xalvakka",
                "requirement_type": "taunt",
                "source": "reviewed fixture",
                "windows": [
                    {
                        "occurrence_id": "boss_active",
                        "target_key": "xalvakka",
                        "active_start_seconds": 0.0,
                        "end_reference": "encounter_end",
                    }
                ],
            }
        ],
    )

    rows = audit_encounter("xalvakka", registry=registry)

    assert len(rows) == 1
    assert rows[0].disposition == "taunt_maintenance_horizon"
    assert rows[0].reviewed is True
    assert rows[0].executable_before_horizon_materialization is False


def test_production_registry_reviews_taleria_ownership_without_pretending_xalvakka_is_resolved():
    registry = RotationAssignmentPolicyRegistryService()

    taleria = audit_encounter("taleria_hm", registry=registry)
    xalvakka = audit_encounter("xalvakka", registry=registry)

    assert len(taleria) == 1
    assert taleria[0].requirement_id == "taleria_hm:tank:boss_taunt"
    assert taleria[0].disposition == "taunt_maintenance_horizon"
    assert taleria[0].reviewed is True
    assert taleria[0].executable_before_horizon_materialization is False

    assert len(xalvakka) == 1
    assert xalvakka[0].requirement_id == "xalvakka:tank:boss_taunt"
    assert xalvakka[0].disposition == "missing"
    assert xalvakka[0].reviewed is False
