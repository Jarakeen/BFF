from types import SimpleNamespace

import pytest

from services.rotation_assignment_taunt_maintenance_horizon_policy_service import (
    RotationAssignmentTauntMaintenanceHorizonPolicy,
    RotationAssignmentTauntMaintenanceHorizonPolicyService,
    RotationAssignmentTauntMaintenanceHorizonWindow,
)
from services.rotation_assignment_taunt_maintenance_service import (
    RotationAssignmentTauntMaintenancePolicy,
    RotationAssignmentTauntMaintenanceWindow,
)
from services.rotation_tank_encounter_horizon_service import RotationTankEncounterHorizon
from ui.rotation_generate_tank_assignment_context_support import (
    RotationGenerateTankAssignmentContextSupport,
    RotationGenerateTankAssignmentEvidence,
)


class _Adapter:
    def adapt(self, _build, *, character_id=None):
        return SimpleNamespace(build=object(), unresolved=())


class _BundleService:
    def __init__(self) -> None:
        self.calls = []

    def compose(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            encounter_id=kwargs["encounter_id"],
            taunt_application_requirements=(),
            taunt_maintenance_requirements=("maintain",),
            defensive_obligations=(),
        )


class _HorizonService:
    def __init__(self, horizon: RotationTankEncounterHorizon) -> None:
        self.horizon = horizon
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return self.horizon


def _symbolic() -> RotationAssignmentTauntMaintenanceHorizonPolicy:
    return RotationAssignmentTauntMaintenanceHorizonPolicy(
        requirement_id="taleria_hm:tank:boss_taunt",
        encounter_id="taleria_hm",
        requirement_type="taunt",
        source_skill_name="Pierce Armor",
        source="reviewed raid Tank responsibility",
        windows=(
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="boss_ownership",
                target_key="boss",
                active_start_seconds=0.0,
                end_reference="encounter_end",
                bar="front",
            ),
        ),
    )


def _concrete(end_seconds: float = 55.0) -> RotationAssignmentTauntMaintenancePolicy:
    return RotationAssignmentTauntMaintenancePolicy(
        requirement_id="taleria_hm:tank:boss_taunt",
        encounter_id="taleria_hm",
        requirement_type="taunt",
        source_skill_name="Pierce Armor",
        source="reviewed raid Tank responsibility",
        windows=(
            RotationAssignmentTauntMaintenanceWindow(
                occurrence_id="boss_ownership",
                target_key="boss",
                active_start_seconds=0.0,
                active_end_seconds=end_seconds,
                bar="front",
            ),
        ),
    )


def _bundle():
    thresholds = object()
    return SimpleNamespace(
        encounter_id="taleria_hm",
        health_threshold_projection=thresholds,
    )


def test_generate_materializes_symbolic_taunt_maintenance_to_projected_encounter_end():
    bundle_service = _BundleService()
    horizon_service = _HorizonService(
        RotationTankEncounterHorizon(
            encounter_id="taleria_hm",
            end_seconds=55.0,
            resolved=True,
            evidence=("projected from explicit raid DPS trajectory",),
        )
    )
    support = RotationGenerateTankAssignmentContextSupport(
        database_path="eso.db",
        build_adapter=_Adapter(),
        bundle_service=bundle_service,
        encounter_horizon_service=horizon_service,
        horizon_policy_service=RotationAssignmentTauntMaintenanceHorizonPolicyService(),
    )
    support.set_evidence(
        (
            RotationGenerateTankAssignmentEvidence(
                encounter_id="taleria_hm",
                member_id="tank-a",
                taunt_maintenance_horizon_policies=(_symbolic(),),
            ),
        )
    )
    evidence_bundle = _bundle()

    result = support.context_for(object(), evidence_bundle)

    assert result.taunt_maintenance_requirements == ("maintain",)
    assert horizon_service.calls == [
        {
            "encounter_id": "taleria_hm",
            "health_threshold_projection": evidence_bundle.health_threshold_projection,
        }
    ]
    policies = bundle_service.calls[0]["taunt_maintenance_policies"]
    assert len(policies) == 1
    assert policies[0].requirement_id == "taleria_hm:tank:boss_taunt"
    assert policies[0].windows[0].active_start_seconds == 0.0
    assert policies[0].windows[0].active_end_seconds == 55.0
    assert policies[0].windows[0].target_key == "boss"


def test_generate_fails_closed_when_symbolic_taunt_maintenance_horizon_is_unresolved():
    bundle_service = _BundleService()
    support = RotationGenerateTankAssignmentContextSupport(
        database_path="eso.db",
        build_adapter=_Adapter(),
        bundle_service=bundle_service,
        encounter_horizon_service=_HorizonService(
            RotationTankEncounterHorizon(
                encounter_id="taleria_hm",
                end_seconds=None,
                resolved=False,
                unresolved=("raid damage trajectory ends before boss death",),
            )
        ),
        horizon_policy_service=RotationAssignmentTauntMaintenanceHorizonPolicyService(),
    )
    support.set_evidence(
        (
            RotationGenerateTankAssignmentEvidence(
                encounter_id="taleria_hm",
                member_id="tank-a",
                taunt_maintenance_horizon_policies=(_symbolic(),),
            ),
        )
    )

    with pytest.raises(ValueError, match="raid damage trajectory ends before boss death"):
        support.context_for(object(), _bundle())

    assert bundle_service.calls == []


def test_generate_rejects_duplicate_numeric_and_symbolic_maintenance_identity():
    support = RotationGenerateTankAssignmentContextSupport(
        database_path="eso.db",
        build_adapter=_Adapter(),
        bundle_service=_BundleService(),
        encounter_horizon_service=_HorizonService(
            RotationTankEncounterHorizon(
                encounter_id="taleria_hm",
                end_seconds=55.0,
                resolved=True,
            )
        ),
        horizon_policy_service=RotationAssignmentTauntMaintenanceHorizonPolicyService(),
    )
    support.set_evidence(
        (
            RotationGenerateTankAssignmentEvidence(
                encounter_id="taleria_hm",
                member_id="tank-a",
                taunt_maintenance_policies=(_concrete(),),
                taunt_maintenance_horizon_policies=(_symbolic(),),
            ),
        )
    )

    with pytest.raises(ValueError, match="duplicate requirement identity"):
        support.context_for(object(), _bundle())
