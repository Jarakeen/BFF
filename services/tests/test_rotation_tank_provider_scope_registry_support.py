from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.rotation_assignment_taunt_maintenance_horizon_policy_service import (
    RotationAssignmentTauntMaintenanceHorizonPolicy,
    RotationAssignmentTauntMaintenanceHorizonWindow,
)
from services.rotation_tank_provider_scope_service import RotationTankProviderScopeService
from services.saved_build_utility_capability_service import (
    SavedBuildUtilityProviderSource,
    SavedBuildUtilityProviderSourceResolution,
)


class _CapabilityService:
    def audit_build(self, build):
        return SimpleNamespace(
            character_id="tank-a",
            character_name="Tank A",
            build_name=build.BuildName,
        )


class _UtilityCapabilityService:
    def __init__(self, sources=(), unresolved=()):
        self.sources = tuple(sources)
        self.unresolved = tuple(unresolved)
        self.calls = []

    def provider_sources_for(self, **kwargs):
        self.calls.append(kwargs)
        return SavedBuildUtilityProviderSourceResolution(
            capability_type=kwargs["capability_type"],
            sources=self.sources,
            unresolved=self.unresolved,
        )


class _ScopeFactory:
    def __call__(self, **kwargs):
        return SimpleNamespace(baseline_assignments=("assignment",))


class _PolicyRegistry:
    def __init__(self, bundle):
        self.bundle = bundle
        self.calls = []

    def for_encounter(self, encounter_id):
        self.calls.append(encounter_id)
        return self.bundle


class _PolicyResolver:
    def __init__(self, *, ready=True, unresolved=()):
        self.calls = []
        self.ready = ready
        self.unresolved = unresolved

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            member_id=kwargs["member_id"],
            ready=self.ready,
            unresolved=self.unresolved,
        )


def _tank():
    return PlayerBuild(Name="Tank A", BuildName="MT", Role="Tank")


def _symbolic(*, source_skill_name=None, bar=None):
    return RotationAssignmentTauntMaintenanceHorizonPolicy(
        requirement_id="taleria_hm:tank:boss_taunt",
        encounter_id="taleria_hm",
        requirement_type="taunt",
        source_skill_name=source_skill_name,
        source="reviewed Taleria Tank responsibility",
        windows=(
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="boss_ownership",
                target_key="tideborn_taleria",
                active_start_seconds=0.0,
                end_reference="encounter_end",
                bar=bar,
            ),
        ),
    )


def _taunt_source(skill="Pierce Armor", bar="front"):
    return SavedBuildUtilityProviderSource(
        capability_type="taunt",
        skill_name=skill,
        bar=bar,
    )


def test_provider_scope_uses_reviewed_registry_when_explicit_policy_is_absent():
    bundle = SimpleNamespace(
        effect_policies=("effect",),
        taunt_policies=("taunt",),
        taunt_maintenance_policies=("maintenance",),
        taunt_maintenance_horizon_policies=(),
        non_effect_policies=("non-effect",),
    )
    registry = _PolicyRegistry(bundle)
    resolver = _PolicyResolver()
    utility = _UtilityCapabilityService()
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
        utility_capability_service=utility,
        scope_factory=_ScopeFactory(),
        policy_resolver=resolver,
        policy_registry=registry,
    )

    result = service.resolve(
        player_build=_tank(),
        roster_builds=(_tank(),),
        encounter_id="taleria_hm",
    )

    assert result.ready is True
    assert result.taunt_maintenance_horizon_policies == ()
    assert utility.calls == []
    assert registry.calls == ["taleria_hm"]
    call = resolver.calls[0]
    assert call["effect_policies"] == ("effect",)
    assert call["taunt_policies"] == ("taunt",)
    assert call["taunt_maintenance_policies"] == ("maintenance",)
    assert call["non_effect_policies"] == ("non-effect",)


def test_provider_scope_binds_symbolic_registry_policy_to_exact_saved_build_taunt():
    symbolic = _symbolic()
    bundle = SimpleNamespace(
        effect_policies=(),
        taunt_policies=(),
        taunt_maintenance_policies=(),
        taunt_maintenance_horizon_policies=(symbolic,),
        non_effect_policies=(),
    )
    registry = _PolicyRegistry(bundle)
    resolver = _PolicyResolver(
        ready=False,
        unresolved=("assignment awaits executable maintenance policy",),
    )
    utility = _UtilityCapabilityService((_taunt_source(),))
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
        utility_capability_service=utility,
        scope_factory=_ScopeFactory(),
        policy_resolver=resolver,
        policy_registry=registry,
    )

    result = service.resolve(
        player_build=_tank(),
        roster_builds=(_tank(),),
        encounter_id="taleria_hm",
    )

    assert result.ready is False
    assert result.unresolved == ("assignment awaits executable maintenance policy",)
    assert len(result.taunt_maintenance_horizon_policies) == 1
    bound = result.taunt_maintenance_horizon_policies[0]
    assert bound.source_skill_name == "Pierce Armor"
    assert bound.windows[0].bar == "front"
    assert result.taunt_provider_sources == (_taunt_source(),)
    assert resolver.calls[0]["taunt_maintenance_policies"] == ()


def test_provider_scope_keeps_ambiguous_saved_build_taunt_source_unresolved():
    bundle = SimpleNamespace(
        effect_policies=(),
        taunt_policies=(),
        taunt_maintenance_policies=(),
        taunt_maintenance_horizon_policies=(_symbolic(),),
        non_effect_policies=(),
    )
    registry = _PolicyRegistry(bundle)
    resolver = _PolicyResolver(ready=False, unresolved=("awaiting horizon",))
    utility = _UtilityCapabilityService(
        (_taunt_source(), _taunt_source("Inner Rage", "back"))
    )
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
        utility_capability_service=utility,
        scope_factory=_ScopeFactory(),
        policy_resolver=resolver,
        policy_registry=registry,
    )

    result = service.resolve(
        player_build=_tank(),
        roster_builds=(_tank(),),
        encounter_id="taleria_hm",
    )

    assert result.ready is False
    assert result.taunt_maintenance_horizon_policies == ()
    assert any("exactly one canonical saved-build taunt source" in row for row in result.unresolved)


def test_explicit_policy_bypasses_reviewed_registry():
    registry = _PolicyRegistry(
        SimpleNamespace(
            effect_policies=("registry-effect",),
            taunt_policies=(),
            taunt_maintenance_policies=(),
            taunt_maintenance_horizon_policies=(_symbolic(),),
            non_effect_policies=(),
        )
    )
    resolver = _PolicyResolver()
    utility = _UtilityCapabilityService()
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
        utility_capability_service=utility,
        scope_factory=_ScopeFactory(),
        policy_resolver=resolver,
        policy_registry=registry,
    )

    service.resolve(
        player_build=_tank(),
        roster_builds=(_tank(),),
        encounter_id="taleria_hm",
        taunt_policies=("explicit-taunt",),
    )

    assert registry.calls == []
    assert utility.calls == []
    call = resolver.calls[0]
    assert call["effect_policies"] == ()
    assert call["taunt_policies"] == ("explicit-taunt",)


def test_explicit_symbolic_policy_bypasses_reviewed_registry_and_binds_provider_source():
    symbolic = _symbolic()
    registry = _PolicyRegistry(
        SimpleNamespace(
            effect_policies=("registry-effect",),
            taunt_policies=(),
            taunt_maintenance_policies=(),
            taunt_maintenance_horizon_policies=(),
            non_effect_policies=(),
        )
    )
    resolver = _PolicyResolver(ready=False, unresolved=("awaiting horizon",))
    utility = _UtilityCapabilityService((_taunt_source("Inner Rage", "back"),))
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
        utility_capability_service=utility,
        scope_factory=_ScopeFactory(),
        policy_resolver=resolver,
        policy_registry=registry,
    )

    result = service.resolve(
        player_build=_tank(),
        roster_builds=(_tank(),),
        encounter_id="taleria_hm",
        taunt_maintenance_horizon_policies=(symbolic,),
    )

    assert registry.calls == []
    assert result.ready is False
    assert len(result.taunt_maintenance_horizon_policies) == 1
    bound = result.taunt_maintenance_horizon_policies[0]
    assert bound.source_skill_name == "Inner Rage"
    assert bound.windows[0].bar == "back"
    assert resolver.calls[0]["taunt_maintenance_policies"] == ()
