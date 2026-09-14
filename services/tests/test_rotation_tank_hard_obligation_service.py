from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleHardObligationEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_defensive_obligation_service import RotationTankDefensiveObligation
from services.rotation_tank_hard_obligation_service import RotationTankHardObligationService
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
)


def _candidate(candidate_id="tank"):
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Tanky",
            build_name="Main Tank",
            duration_seconds=40.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _application_requirement():
    return RotationTankTauntApplicationRequirement(
        requirement_id="pull_taunt",
        source_skill_name="Pierce Armor",
        window_start_seconds=0.0,
        window_end_seconds=2.0,
        target_key="boss",
    )


def _maintenance_requirement():
    return RotationTankTauntMaintenanceRequirement(
        requirement_id="boss_ownership",
        source_skill_name="Pierce Armor",
        target_key="boss",
        active_start_seconds=0.0,
        active_end_seconds=30.0,
    )


def _defensive_obligation():
    return RotationTankDefensiveObligation(
        obligation_id="heavy_attack",
        window_start_seconds=10.0,
        window_end_seconds=11.0,
        allowed_actions=(RotationActionKind.BLOCK,),
    )


class _TauntApplicationService:
    def __init__(self, *, resolved=True, satisfied=True, unresolved=()):
        self.resolved = resolved
        self.satisfied = satisfied
        self.unresolved = tuple(unresolved)

    def assess(self, *, plan, requirement):
        applications = (object(),) if self.satisfied else ()
        return SimpleNamespace(
            resolved=self.resolved,
            satisfied=self.satisfied,
            applications=applications,
            unresolved=self.unresolved,
        )


class _HardLaneService:
    def __init__(self, *, satisfied, reasons=(), candidate_id=None):
        self.satisfied = satisfied
        self.reasons = tuple(reasons)
        self.candidate_id = candidate_id

    def evaluate_candidate(self, *, candidate, **_kwargs):
        return RotationCandidateRoleHardObligationEvidence(
            candidate_id=self.candidate_id or candidate.candidate_id,
            satisfied=self.satisfied,
            reasons=self.reasons,
        )


def _service(
    *,
    taunt=None,
    maintenance=None,
    defensive=None,
    include_application=True,
    include_maintenance=True,
    include_defensive=True,
):
    return RotationTankHardObligationService(
        "unused.db",
        taunt_application_requirements=(
            (_application_requirement(),) if include_application else ()
        ),
        taunt_maintenance_requirements=(
            (_maintenance_requirement(),) if include_maintenance else ()
        ),
        defensive_obligations=((_defensive_obligation(),) if include_defensive else ()),
        taunt_application_service=taunt or _TauntApplicationService(),
        taunt_maintenance_service=maintenance
        or _HardLaneService(
            satisfied=True,
            reasons=("boss_ownership: target boss continuously taunted for 30s",),
        ),
        defensive_service=defensive
        or _HardLaneService(
            satisfied=True,
            reasons=("heavy_attack: scheduled 1 defensive responses",),
        ),
    )


def test_all_supplied_tank_hard_obligations_compose_to_resolved_pass():
    result = _service().evaluate_plan(_candidate())

    assert result.satisfied is True
    assert result.candidate_id == "tank"
    assert result.reasons == (
        "pull_taunt: scheduled 1 required taunt applications",
        "boss_ownership: target boss continuously taunted for 30s",
        "heavy_attack: scheduled 1 defensive responses",
    )


def test_resolved_hard_failure_dominates_other_unresolved_tank_evidence():
    result = _service(
        taunt=_TauntApplicationService(
            resolved=False,
            satisfied=False,
            unresolved=("pull_taunt: source taunt identity unresolved",),
        ),
        defensive=_HardLaneService(
            satisfied=False,
            reasons=("heavy_attack: scheduled 0 of 1 required defensive responses",),
        ),
    ).evaluate_plan(_candidate())

    assert result.satisfied is False
    assert "source taunt identity unresolved" in result.reasons[0]
    assert "scheduled 0 of 1 required defensive responses" in result.reasons[-1]


def test_unresolved_tank_lane_remains_unresolved_when_no_resolved_failure_exists():
    result = _service(
        taunt=_TauntApplicationService(
            resolved=False,
            satisfied=False,
            unresolved=("pull_taunt: source taunt identity unresolved",),
        ),
        include_maintenance=False,
        include_defensive=False,
    ).evaluate_plan(_candidate())

    assert result.satisfied is None
    assert result.reasons == ("pull_taunt: source taunt identity unresolved",)


def test_missing_all_tank_obligations_is_explicitly_unresolved_not_an_automatic_pass():
    result = _service(
        include_application=False,
        include_maintenance=False,
        include_defensive=False,
    ).evaluate_plan(_candidate())

    assert result.satisfied is None
    assert result.reasons == (
        "tank hard obligation unavailable: no explicit taunt application, taunt maintenance, or defensive obligation supplied",
    )


def test_resolved_taunt_application_failure_is_a_hard_failure():
    result = _service(
        taunt=_TauntApplicationService(resolved=True, satisfied=False),
        include_maintenance=False,
        include_defensive=False,
    ).evaluate_plan(_candidate())

    assert result.satisfied is False
    assert result.reasons == (
        "pull_taunt: scheduled 0 of 1 required taunt applications",
    )


def test_delegated_tank_hard_evidence_must_keep_candidate_identity():
    service = _service(
        maintenance=_HardLaneService(
            satisfied=True,
            candidate_id="other",
        ),
        include_application=False,
        include_defensive=False,
    )

    with pytest.raises(ValueError, match="taunt maintenance evidence candidate mismatch"):
        service.evaluate_plan(_candidate())
