from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_taunt_maintenance_family_projector_service import (
    RotationTankTauntMaintenanceFamilyProjectorService,
)
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
)


def _candidate(candidate_id="baseline", *, unresolved=()):
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Tank",
            build_name="Main Tank",
            duration_seconds=40.0,
            actions=(
                RotationAction(
                    0.0,
                    0,
                    RotationActionKind.SKILL,
                    name="Pierce Armor",
                    bar="front",
                    target_key="boss",
                ),
            ),
            unresolved=tuple(unresolved),
        ),
        refresh_leads=(1.0,),
        action_claims=("existing",),
    )


def _requirement():
    return RotationTankTauntMaintenanceRequirement(
        requirement_id="boss_maintenance",
        source_skill_name="Pierce Armor",
        target_key="boss",
        active_start_seconds=0.0,
        active_end_seconds=30.0,
        bar="front",
    )


class _CandidateService:
    def __init__(self, projection):
        self.projection = projection
        self.calls = []

    def project(self, **kwargs):
        self.calls.append(kwargs)
        return self.projection


def test_resolved_projection_replaces_only_that_candidate_and_preserves_identity():
    original = _candidate()
    projected = GeneratedRotationCandidate(
        candidate_id="baseline",
        plan=RotationPlan(
            character_name="Tank",
            build_name="Main Tank",
            duration_seconds=40.0,
            actions=original.plan.actions
            + (
                RotationAction(
                    14.0,
                    0,
                    RotationActionKind.SKILL,
                    name="Pierce Armor",
                    bar="front",
                    target_key="boss",
                ),
            ),
        ),
        refresh_leads=original.refresh_leads,
        action_claims=original.action_claims,
    )
    service = _CandidateService(
        SimpleNamespace(candidate=projected, unresolved=())
    )
    projector = RotationTankTauntMaintenanceFamilyProjectorService(
        requirements=(_requirement(),),
        candidate_service=service,
    )

    result = projector(original)

    assert result is projected
    assert result.candidate_id == "baseline"
    assert service.calls[0]["candidate"] is original
    assert service.calls[0]["requirements"] == (_requirement(),)


def test_unresolved_projection_stays_candidate_local_and_preserves_schedule_metadata():
    original = _candidate(unresolved=("preexisting",))
    service = _CandidateService(
        SimpleNamespace(
            candidate=None,
            unresolved=(
                "boss_maintenance: refresh slot 14s is occupied",
                "boss_maintenance: refresh slot 14s is occupied",
            ),
        )
    )
    projector = RotationTankTauntMaintenanceFamilyProjectorService(
        requirements=(_requirement(),),
        candidate_service=service,
    )

    result = projector(original)

    assert result.candidate_id == original.candidate_id
    assert result.plan.actions == original.plan.actions
    assert result.refresh_leads == original.refresh_leads
    assert result.action_claims == original.action_claims
    assert result.plan.unresolved == (
        "preexisting",
        "boss_maintenance: refresh slot 14s is occupied",
    )


def test_empty_projection_reason_gets_explicit_family_unresolved_marker():
    original = _candidate()
    projector = RotationTankTauntMaintenanceFamilyProjectorService(
        requirements=(_requirement(),),
        candidate_service=_CandidateService(
            SimpleNamespace(candidate=None, unresolved=())
        ),
    )

    result = projector(original)

    assert result.plan.unresolved == (
        "tank taunt maintenance family projection unresolved",
    )


def test_projector_rejects_candidate_identity_mutation():
    original = _candidate("baseline")
    illegal = _candidate("not_baseline")
    projector = RotationTankTauntMaintenanceFamilyProjectorService(
        requirements=(_requirement(),),
        candidate_service=_CandidateService(
            SimpleNamespace(candidate=illegal, unresolved=())
        ),
    )

    with pytest.raises(ValueError, match="must preserve candidate identity"):
        projector(original)
