from types import SimpleNamespace

import pytest

from models.build_model import PlayerBuild
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.rotation_tank_provider_scope_service import RotationTankProviderScopeService


class _CapabilityService:
    def __init__(self, member_id="tank-a"):
        self.member_id = member_id
        self.calls = []

    def audit_build(self, build):
        self.calls.append(build)
        return SimpleNamespace(
            character_id=self.member_id,
            character_name=getattr(build, "Name", "Tank A"),
            build_name=getattr(build, "BuildName", "Tank Build"),
        )


class _ScopeFactory:
    def __init__(self, assignments=()):
        self.assignments = tuple(assignments)
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(baseline_assignments=self.assignments)


class _PolicyResolver:
    def __init__(self, *, member_id="tank-a", ready=True, unresolved=()):
        self.member_id = member_id
        self.ready = ready
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            member_id=self.member_id,
            ready=self.ready,
            unresolved=self.unresolved,
        )


def _tank():
    return PlayerBuild(Name="Tank A", BuildName="MT", Role="Tank")


def _assignment(requirement_id: str) -> ProviderAssignment:
    return ProviderAssignment(
        requirement_id=requirement_id,
        encounter_id="test-encounter",
        requirement_type="test",
        status=ProviderAssignmentStatus.INSUFFICIENT,
        primary_providers=(),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="test assignment",
    )


def test_provider_scope_reuses_canonical_scope_and_policy_resolver():
    assignments = (_assignment("req-a"), _assignment("req-b"))
    capability = _CapabilityService()
    scope_factory = _ScopeFactory(assignments)
    policy = _PolicyResolver(ready=True)
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=capability,
        scope_factory=scope_factory,
        policy_resolver=policy,
    )
    roster = (_tank(), PlayerBuild(Name="Healer", BuildName="H", Role="Healer"))
    taunt_policy = object()
    maintenance_policy = object()
    effect_policy = object()
    non_effect_policy = object()

    result = service.resolve(
        player_build=roster[0],
        roster_builds=roster,
        encounter_id="taleria_hm",
        effect_policies=(effect_policy,),
        taunt_policies=(taunt_policy,),
        taunt_maintenance_policies=(maintenance_policy,),
        non_effect_policies=(non_effect_policy,),
    )

    assert result.encounter_id == "taleria_hm"
    assert result.member_id == "tank-a"
    assert result.assignments == assignments
    assert result.ready is True
    assert result.unresolved == ()
    assert capability.calls == [roster[0]]
    scope_call = scope_factory.calls[0]
    assert scope_call["encounter_id"] == "taleria_hm"
    assert scope_call["member_id"] == "tank-a"
    assert scope_call["roster_builds"] == roster
    policy_call = policy.calls[0]
    assert policy_call["member_id"] == "tank-a"
    assert policy_call["assignments"] == assignments
    assert policy_call["effect_policies"] == (effect_policy,)
    assert policy_call["taunt_policies"] == (taunt_policy,)
    assert policy_call["taunt_maintenance_policies"] == (maintenance_policy,)
    assert policy_call["non_effect_policies"] == (non_effect_policy,)


def test_provider_scope_preserves_missing_policy_as_unresolved_not_empty_success():
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
        scope_factory=_ScopeFactory((_assignment("req-a"),)),
        policy_resolver=_PolicyResolver(
            ready=False,
            unresolved=("Owned encounter assignment has no explicit rotation policy disposition",),
        ),
    )

    result = service.resolve(
        player_build=_tank(),
        roster_builds=(_tank(),),
        encounter_id="xalvakka_hm",
    )

    assert result.ready is False
    assert result.unresolved == (
        "Owned encounter assignment has no explicit rotation policy disposition",
    )


def test_provider_scope_rejects_non_tank_and_missing_team_context():
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(),
        scope_factory=_ScopeFactory(),
        policy_resolver=_PolicyResolver(),
    )

    with pytest.raises(ValueError, match="explicit Tank saved-build role"):
        service.resolve(
            player_build=PlayerBuild(Name="H", BuildName="H", Role="Healer"),
            roster_builds=(_tank(),),
            encounter_id="taleria_hm",
        )

    with pytest.raises(ValueError, match="exact selected-team saved builds"):
        service.resolve(
            player_build=_tank(),
            roster_builds=(),
            encounter_id="taleria_hm",
        )


def test_provider_scope_rejects_policy_resolver_member_mismatch():
    service = RotationTankProviderScopeService(
        data_root="data",
        database_path="data/eso.db",
        build_service=object(),
        capability_service=_CapabilityService(member_id="tank-a"),
        scope_factory=_ScopeFactory(),
        policy_resolver=_PolicyResolver(member_id="tank-b"),
    )

    with pytest.raises(ValueError, match="member mismatch"):
        service.resolve(
            player_build=_tank(),
            roster_builds=(_tank(),),
            encounter_id="taleria_hm",
        )
