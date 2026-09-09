from types import SimpleNamespace

import pytest

from minmax.character_progression import CharacterProgression
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.team_provider_coverage_service import (
    TeamProviderCoverageProfile,
    TeamProviderCoverageService,
)
from services.team_provider_temporal_coverage_service import (
    TeamProviderTemporalCoverageService,
    TeamProviderTemporalRequirement,
    TeamProviderTimedApplication,
)
from services.team_provider_workload_candidate_service import (
    TeamProviderActionBinding,
    TeamProviderWorkloadAlternativeRequest,
    TeamProviderWorkloadCandidateService,
)


class _CanonicalWorkloadSpy:
    def __init__(self):
        self.calls = []

    def project_from_coverage(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(workload=kwargs["alternative_id"])


def _build(name="Magrat", build_name="Trial Healer"):
    return PlayerBuild(Name=name, BuildName=build_name)


def _plan(name="Magrat", build_name="Trial Healer"):
    return RotationPlan(
        character_name=name,
        build_name=build_name,
        duration_seconds=60.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(8.0, 0, RotationActionKind.SKILL, "Healing Springs", "back"),
            RotationAction(20.0, 1, RotationActionKind.SKILL, "Combat Prayer", "front"),
        ),
    )


def _request(action="Combat Prayer"):
    recipient = TeamProviderCoverageService.evaluate(
        TeamProviderCoverageProfile("minor_berserk", 12),
        required_recipients=12,
    )
    temporal = TeamProviderTemporalCoverageService.evaluate(
        TeamProviderTemporalRequirement("minor_berserk", 0.0, 60.0),
        applications=(
            TeamProviderTimedApplication("minor_berserk", "Magrat", 0.0, 60.0),
        ),
    )
    return TeamProviderWorkloadAlternativeRequest(
        alternative_id="prayer cadence",
        effect_key="minor_berserk",
        duration_seconds=60.0,
        recipient_coverage_result=recipient,
        temporal_coverage_result=temporal,
        action_bindings=(
            TeamProviderActionBinding(
                "Magrat", "Trial Healer", action, 0.25
            ),
        ),
        gcd_seconds_per_application=1.0,
    )


def test_projects_every_exact_scheduled_provider_cast_for_selected_build():
    spy = _CanonicalWorkloadSpy()
    service = TeamProviderWorkloadCandidateService(canonical_workload=spy)
    progression = CharacterProgression()

    result = service.generate(
        selected_builds=(_build(),),
        rotation_plans=(_plan(),),
        progression_by_identity={("Magrat", "Trial Healer"): progression},
        alternatives=(_request(),),
    )

    assert result.workloads == ("prayer cadence",)
    assert result.rejected == ()
    contribution = spy.calls[0]["contributions"][0]
    assert contribution.build is not None
    assert contribution.progression is progression
    assert tuple(
        (item.time_seconds, item.sequence, item.primary_role_displacement_seconds)
        for item in contribution.provider_actions
    ) == ((0.0, 0, 0.25), (20.0, 1, 0.25))


def test_rejects_missing_plan_instead_of_treating_static_build_as_uptime():
    spy = _CanonicalWorkloadSpy()
    result = TeamProviderWorkloadCandidateService(canonical_workload=spy).generate(
        selected_builds=(_build(),),
        rotation_plans=(),
        progression_by_identity={
            ("Magrat", "Trial Healer"): CharacterProgression()
        },
        alternatives=(_request(),),
    )

    assert result.projections == ()
    assert "no exact rotation plan is attached" in result.rejected[0].blockers[0]
    assert spy.calls == []


def test_action_matching_is_exact_and_never_fuzzy():
    result = TeamProviderWorkloadCandidateService(
        canonical_workload=_CanonicalWorkloadSpy()
    ).generate(
        selected_builds=(_build(),),
        rotation_plans=(_plan(),),
        progression_by_identity={
            ("Magrat", "Trial Healer"): CharacterProgression()
        },
        alternatives=(_request("Prayer"),),
    )

    assert result.projections == ()
    assert "'Prayer' is not scheduled" in result.rejected[0].blockers[0]


def test_rejects_noncanonical_effect_identity():
    with pytest.raises(ValueError, match="lower-snake-case"):
        request = _request()
        TeamProviderWorkloadAlternativeRequest(
            alternative_id=request.alternative_id,
            effect_key="Minor Berserk",
            duration_seconds=request.duration_seconds,
            recipient_coverage_result=request.recipient_coverage_result,
            temporal_coverage_result=request.temporal_coverage_result,
            action_bindings=request.action_bindings,
            gcd_seconds_per_application=1.0,
        )
