from types import SimpleNamespace

from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
    EncounterThresholdClockPoint,
)
from services.rotation_assignment_taunt_maintenance_horizon_policy_service import (
    RotationAssignmentTauntMaintenanceHorizonPolicy,
    RotationAssignmentTauntMaintenanceHorizonPolicyService,
    RotationAssignmentTauntMaintenanceHorizonWindow,
)
from services.rotation_tank_encounter_horizon_service import RotationTankEncounterHorizon
from services.rotation_tank_encounter_transition_timing_service import (
    RotationTankEncounterTransitionBoundary,
    RotationTankEncounterTransitionTiming,
)
from ui.rotation_generate_tank_assignment_context_support import (
    RotationGenerateTankAssignmentContextSupport,
    RotationGenerateTankAssignmentEvidence,
)


class _Adapter:
    def adapt(self, _build, *, character_id=None):
        return SimpleNamespace(build=object(), unresolved=())


class _BundleService:
    def __init__(self):
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
    def resolve(self, **_kwargs):
        return RotationTankEncounterHorizon(
            encounter_id="xalvakka",
            end_seconds=100.0,
            resolved=True,
            evidence=("base end",),
        )


class _TransitionService:
    def __init__(self):
        self.calls = []

    def project(self, **kwargs):
        self.calls.append(kwargs)
        return RotationTankEncounterTransitionTiming(
            encounter_id="xalvakka",
            boundaries=(
                RotationTankEncounterTransitionBoundary(
                    threshold_fraction=0.70,
                    crossing_time_seconds=30.0,
                    resume_time_seconds=78.8095,
                    reviewed_delay_seconds=48.8095,
                    observed_min_delay_seconds=44.437,
                    observed_max_delay_seconds=65.064,
                    sample_count=4,
                    source="reviewed 70 evidence",
                ),
                RotationTankEncounterTransitionBoundary(
                    threshold_fraction=0.40,
                    crossing_time_seconds=108.8095,
                    resume_time_seconds=173.3705,
                    reviewed_delay_seconds=64.561,
                    observed_min_delay_seconds=62.266,
                    observed_max_delay_seconds=66.376,
                    sample_count=3,
                    source="reviewed 40 evidence",
                ),
            ),
            adjusted_end_seconds=213.3705,
            resolved=True,
            evidence=("reviewed transition timing",),
        )


def _projection():
    return EncounterHealthThresholdProjection(
        encounter_id="xalvakka",
        difficulty="hardmode",
        maximum_health=100_000_000,
        trajectory=object(),
        points=(
            EncounterThresholdClockPoint(
                fact_key="retreat_70",
                label="70 retreat",
                threshold_fraction=0.70,
                time_seconds=30.0,
                resolved=True,
                reason="projected",
            ),
            EncounterThresholdClockPoint(
                fact_key="retreat_40",
                label="40 retreat",
                threshold_fraction=0.40,
                time_seconds=60.0,
                resolved=True,
                reason="projected",
            ),
        ),
        unresolved=(),
    )


def _policy():
    return RotationAssignmentTauntMaintenanceHorizonPolicy(
        requirement_id="xalvakka:tank:boss_taunt",
        encounter_id="xalvakka",
        requirement_type="taunt",
        source_skill_name="Pierce Armor",
        source="reviewed Xalvakka ownership",
        windows=(
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="phase_1",
                target_key="xalvakka",
                active_start_seconds=0.0,
                end_reference="health_threshold:70%",
            ),
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="phase_2",
                target_key="xalvakka",
                start_reference="transition_resume:70%",
                end_reference="health_threshold:40%",
            ),
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="phase_3",
                target_key="xalvakka",
                start_reference="transition_resume:40%",
                end_reference="encounter_end",
            ),
        ),
    )


def test_generate_materializes_three_transition_adjusted_xalvakka_ownership_windows():
    bundle_service = _BundleService()
    transition_service = _TransitionService()
    support = RotationGenerateTankAssignmentContextSupport(
        database_path="eso.db",
        build_adapter=_Adapter(),
        bundle_service=bundle_service,
        encounter_horizon_service=_HorizonService(),
        encounter_transition_timing_service=transition_service,
        horizon_policy_service=RotationAssignmentTauntMaintenanceHorizonPolicyService(),
    )
    support.set_evidence(
        (
            RotationGenerateTankAssignmentEvidence(
                encounter_id="xalvakka",
                member_id="tank-a",
                taunt_maintenance_horizon_policies=(_policy(),),
            ),
        )
    )
    evidence_bundle = SimpleNamespace(
        encounter_id="xalvakka",
        health_threshold_projection=_projection(),
    )

    result = support.context_for(object(), evidence_bundle)

    assert result.taunt_maintenance_requirements == ("maintain",)
    assert len(transition_service.calls) == 1
    policy = bundle_service.calls[0]["taunt_maintenance_policies"][0]
    assert [
        (window.active_start_seconds, window.active_end_seconds)
        for window in policy.windows
    ] == [
        (0.0, 30.0),
        (78.8095, 108.8095),
        (173.3705, 213.3705),
    ]
