from services.rotation_assignment_taunt_maintenance_horizon_policy_service import (
    RotationAssignmentTauntMaintenanceHorizonPolicy,
    RotationAssignmentTauntMaintenanceHorizonPolicyService,
    RotationAssignmentTauntMaintenanceHorizonWindow,
)
from services.rotation_tank_encounter_horizon_service import RotationTankEncounterHorizon


def _policy(*, start: float = 0.0):
    return RotationAssignmentTauntMaintenanceHorizonPolicy(
        requirement_id="xalvakka:tank:boss_taunt",
        encounter_id="xalvakka",
        requirement_type="taunt",
        source_skill_name="Pierce Armor",
        source="reviewed raid Tank responsibility",
        windows=(
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="boss_ownership",
                target_key="boss",
                active_start_seconds=start,
                end_reference="encounter_end",
                bar="front",
            ),
        ),
    )


def test_resolved_horizon_materializes_existing_numeric_maintenance_policy():
    horizon = RotationTankEncounterHorizon(
        encounter_id="xalvakka",
        end_seconds=107.116512,
        resolved=True,
        evidence=("projected fight end",),
    )

    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(),
        horizon=horizon,
    )

    assert result.resolved is True
    assert result.policy is not None
    assert result.policy.requirement_id == "xalvakka:tank:boss_taunt"
    assert result.policy.source_skill_name == "Pierce Armor"
    assert result.policy.windows[0].active_start_seconds == 0.0
    assert result.policy.windows[0].active_end_seconds == 107.116512
    assert result.policy.windows[0].target_key == "boss"
    assert result.policy.windows[0].bar == "front"
    assert any("symbolic_endpoint=encounter_end" in row for row in result.evidence)


def test_unresolved_horizon_fails_closed_without_numeric_policy():
    horizon = RotationTankEncounterHorizon(
        encounter_id="xalvakka",
        end_seconds=None,
        resolved=False,
        unresolved=("damage trajectory ends before boss death",),
    )

    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(),
        horizon=horizon,
    )

    assert result.resolved is False
    assert result.policy is None
    assert result.unresolved == ("damage trajectory ends before boss death",)


def test_horizon_encounter_identity_must_match_policy():
    horizon = RotationTankEncounterHorizon(
        encounter_id="taleria",
        end_seconds=30.0,
        resolved=True,
    )

    try:
        RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
            policy=_policy(),
            horizon=horizon,
        )
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("foreign encounter horizon must fail closed")


def test_projected_end_must_follow_reviewed_maintenance_start():
    horizon = RotationTankEncounterHorizon(
        encounter_id="xalvakka",
        end_seconds=20.0,
        resolved=True,
    )

    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(start=20.0),
        horizon=horizon,
    )

    assert result.resolved is False
    assert result.policy is None
    assert "does not occur after" in result.unresolved[0]
