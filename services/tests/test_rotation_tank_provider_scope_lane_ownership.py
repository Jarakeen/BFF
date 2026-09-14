from types import SimpleNamespace

from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.encounter_provider_candidate import (
    ProviderCandidate,
    ProviderCandidateStatus,
)
from services.rotation_assignment_taunt_maintenance_horizon_policy_service import (
    RotationAssignmentTauntMaintenanceHorizonPolicy,
    RotationAssignmentTauntMaintenanceHorizonWindow,
)
from services.rotation_tank_provider_scope_service import RotationTankProviderScopeService
from services.saved_build_utility_capability_service import SavedBuildUtilityProviderSource


def _candidate(member_id):
    return ProviderCandidate(
        requirement_id="xalvakka:tank:boss_taunt",
        encounter_id="xalvakka",
        requirement_type="taunt",
        member_id=member_id,
        character_name=member_id,
        build_name=f"{member_id} build",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("canonical taunt",),
    )


def _assignment():
    return ProviderAssignment(
        requirement_id="xalvakka:tank:boss_taunt",
        encounter_id="xalvakka",
        requirement_type="taunt",
        status=ProviderAssignmentStatus.UNRESOLVED_SELECTION,
        primary_providers=(),
        backup_providers=(_candidate("tank-a"), _candidate("tank-b")),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="two viable Tanks",
    )


def _policy():
    return RotationAssignmentTauntMaintenanceHorizonPolicy(
        requirement_id="xalvakka:tank:boss_taunt",
        encounter_id="xalvakka",
        requirement_type="taunt",
        source="reviewed fixture",
        windows=(
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="phase_1",
                target_key="xalvakka",
                active_start_seconds=0.0,
                end_reference="encounter_end",
            ),
        ),
    )


class _CapabilityService:
    def audit_build(self, build):
        return SimpleNamespace(
            character_id=build.MemberId,
            character_name=build.MemberId,
            build_name=build.MemberId,
        )


class _UtilityService:
    def provider_sources_for(self, *, build, capability_type):
        assert capability_type == "taunt"
        return SimpleNamespace(
            sources=(
                SavedBuildUtilityProviderSource(
                    capability_type="taunt",
                    skill_name="Pierce Armor",
                    bar="front",
                ),
            ),
            unresolved=(),
        )


class _Registry:
    def for_encounter(self, _encounter_id):
        return SimpleNamespace(
            effect_policies=(),
            taunt_policies=(),
            taunt_maintenance_policies=(),
            taunt_maintenance_horizon_policies=(_policy(),),
            non_effect_policies=(),
        )


class _Resolver:
    def resolve(self, *, member_id, **_kwargs):
        return SimpleNamespace(
            member_id=member_id,
            ready=True,
            unresolved=(),
            taunt_policies=(),
            taunt_maintenance_policies=(),
        )


def _scope_factory(**_kwargs):
    return SimpleNamespace(baseline_assignments=(_assignment(),))


def _service():
    return RotationTankProviderScopeService(
        data_root="data",
        database_path="eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
        utility_capability_service=_UtilityService(),
        scope_factory=_scope_factory,
        policy_resolver=_Resolver(),
        policy_registry=_Registry(),
    )


def _tank(member_id):
    return SimpleNamespace(MemberId=member_id, Role="Tank")


def test_boss_holder_receives_symbolic_boss_ownership_policy():
    result = _service().resolve(
        player_build=_tank("tank-a"),
        roster_builds=(_tank("tank-a"), _tank("tank-b")),
        encounter_id="xalvakka",
        preferred_member_by_requirement={
            "xalvakka:tank:boss_taunt": "tank-a",
        },
    )

    assert result.assignments[0].status is ProviderAssignmentStatus.ASSIGNED
    assert result.assignments[0].primary_providers[0].member_id == "tank-a"
    assert len(result.taunt_maintenance_horizon_policies) == 1
    assert result.taunt_maintenance_horizon_policies[0].source_skill_name == "Pierce Armor"


def test_add_handler_does_not_inherit_boss_ownership_policy_just_for_having_taunt():
    result = _service().resolve(
        player_build=_tank("tank-b"),
        roster_builds=(_tank("tank-a"), _tank("tank-b")),
        encounter_id="xalvakka",
        preferred_member_by_requirement={
            "xalvakka:tank:boss_taunt": "tank-a",
        },
    )

    assert result.assignments[0].status is ProviderAssignmentStatus.ASSIGNED
    assert result.assignments[0].primary_providers[0].member_id == "tank-a"
    assert result.taunt_maintenance_horizon_policies == ()
    assert result.taunt_provider_sources == ()
