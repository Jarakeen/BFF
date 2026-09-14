import json

from services.rotation_tank_taunt_state_lifecycle_service import (
    RotationTankTauntStateLifecycleService,
)


def test_reviewed_taunt_state_identity_loads(tmp_path):
    path = tmp_path / "reviewed.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "states": [
                    {
                        "state_id": "taunt",
                        "ability_id": 38254,
                        "effect_name": "Taunt",
                        "scope": "source_target_debuff_state",
                        "reviewed": True,
                        "evidence": ["fixture"],
                        "interpretation": "fixture interpretation",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    row = RotationTankTauntStateLifecycleService(path).reviewed_for("taunt")
    assert row is not None
    assert row.ability_id == 38254
    assert row.effect_name == "Taunt"
    assert row.scope == "source_target_debuff_state"


def test_reviewed_taunt_state_rejects_unreviewed_rows(tmp_path):
    path = tmp_path / "reviewed.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "states": [
                    {
                        "state_id": "taunt",
                        "ability_id": 38254,
                        "effect_name": "Taunt",
                        "scope": "source_target_debuff_state",
                        "reviewed": False,
                        "evidence": ["fixture"],
                        "interpretation": "fixture interpretation",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    try:
        RotationTankTauntStateLifecycleService(path)
    except ValueError as exc:
        assert "must be reviewed" in str(exc)
    else:
        raise AssertionError("expected unreviewed taunt state to fail")
