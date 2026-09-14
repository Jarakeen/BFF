from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.rotation_tank_provider_scope_service import RotationTankProviderScopeService


class _CapabilityService:
    def audit_build(self, build):
        return SimpleNamespace(
            character_id="tank-a",
            character_name="Tank A",
            build_name=build.BuildName,
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
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
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
    assert registry.calls == ["taleria_hm"]
    call = resolver.calls[0]
    assert call["effect_policies"] == ("effect",)
    assert call["taunt_policies"] == ("taunt",)
    assert call["taunt_maintenance_policies"] == ("maintenance",)
    assert call["non_effect_policies"] == ("non-effect",)


def test_provider_scope_preserves_symbolic_registry_policy_without_calling_it_executable():
    symbolic = object()
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
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
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
    assert result.taunt_maintenance_horizon_policies == (symbolic,)
    assert result.unresolved == ("assignment awaits executable maintenance policy",)
    assert resolver.calls[0]["taunt_maintenance_policies"] == ()


def test_explicit_policy_bypasses_reviewed_registry():
    registry = _PolicyRegistry(
        SimpleNamespace(
            effect_policies=("registry-effect",),
            taunt_policies=(),
            taunt_maintenance_policies=(),
            taunt_maintenance_horizon_policies=("registry-symbolic",),
            non_effect_policies=(),
        )
    )
    resolver = _PolicyResolver()
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
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
    call = resolver.calls[0]
    assert call["effect_policies"] == ()
    assert call["taunt_policies"] == ("explicit-taunt",)


def test_explicit_symbolic_policy_bypasses_reviewed_registry_and_remains_non_executable():
    symbolic = object()
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
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
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
    assert result.taunt_maintenance_horizon_policies == (symbolic,)
    assert resolver.calls[0]["taunt_maintenance_policies"] == ()
