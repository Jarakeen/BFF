from __future__ import annotations

import pytest

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.role import Role
from services.encounter_provider_assignment import ProviderAssignment, ProviderAssignmentStatus
from services.encounter_provider_candidate import ProviderCandidate, ProviderCandidateStatus
from services.rotation_assignment_candidate_evaluation_service import (
    RotationAssignmentCandidateEvaluationService,
)
from services.rotation_assignment_effect_obligation_service import (
    RotationAssignmentEffectPolicy,
)


class _CandidateEvaluatorSpy:
    def __init__(self) -> None:
        self.calls = []

    def evaluate_and_rank(self, **kwargs):
        self.calls.append(kwargs)
        return ()


def _build(*, name: str = "DF Healer") -> CharacterBuild:
    return CharacterBuild(
        name=name,
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        character_id="char-a",
        character_name="Magrat",
    )


def _provider(*, member_id: str = "char-a", build_name: str = "DF Healer") -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id="major_brittle",
        encounter_id="xalvakka_hm",
        requirement_type="major_brittle",
        member_id=member_id,
        character_name="Magrat",
        build_name=build_name,
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("verified capability",),
    )


def _assignment(*, provider: ProviderCandidate | None = None) -> ProviderAssignment:
    return ProviderAssignment(
        requirement_id="major_brittle",
        encounter_id="xalvakka_hm",
        requirement_type="major_brittle",
        status=ProviderAssignmentStatus.ASSIGNED,
        primary_providers=() if provider is None else (provider,),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="test",
    )


def _policy() -> RotationAssignmentEffectPolicy:
    return RotationAssignmentEffectPolicy(
        requirement_id="major_brittle",
        encounter_id="xalvakka_hm",
        requirement_type="major_brittle",
        effect_name="chilled",
        source_skill_name="Winter's Revenge",
        minimum_uptime=0.90,
        bar="back",
        source="verified rotation assignment policy",
    )


def test_assignment_owned_by_build_is_forwarded_as_effect_requirement() -> None:
    candidate_spy = _CandidateEvaluatorSpy()
    service = RotationAssignmentCandidateEvaluationService(candidate_service=candidate_spy)

    result = service.evaluate_and_rank(
        build=_build(),
        member_id="char-a",
        assignments=(_assignment(provider=_provider()),),
        policies=(_policy(),),
        candidates=(),
    )

    assert len(result.obligation_projection.requirements) == 1
    requirement = result.obligation_projection.requirements[0]
    assert requirement.effect_name == "chilled"
    assert requirement.source_skill_name == "Winter's Revenge"
    assert requirement.minimum_uptime == pytest.approx(0.90)
    assert requirement.bar == "back"
    assert candidate_spy.calls[0]["requirements"] == (requirement,)
    assert result.ranked_candidates == ()


def test_assignment_owned_by_other_member_forwards_no_effect_requirement() -> None:
    candidate_spy = _CandidateEvaluatorSpy()
    service = RotationAssignmentCandidateEvaluationService(candidate_service=candidate_spy)

    result = service.evaluate_and_rank(
        build=_build(),
        member_id="char-a",
        assignments=(_assignment(provider=_provider(member_id="char-b")),),
        policies=(_policy(),),
        candidates=(),
    )

    assert result.obligation_projection.requirements == ()
    assert candidate_spy.calls[0]["requirements"] == ()


def test_build_identity_mismatch_stops_before_candidate_evaluation() -> None:
    candidate_spy = _CandidateEvaluatorSpy()
    service = RotationAssignmentCandidateEvaluationService(candidate_service=candidate_spy)

    with pytest.raises(ValueError, match="provider build does not match"):
        service.evaluate_and_rank(
            build=_build(name="DF Healer"),
            member_id="char-a",
            assignments=(_assignment(provider=_provider(build_name="GH Healer")),),
            policies=(_policy(),),
            candidates=(),
        )

    assert candidate_spy.calls == []


def test_assignment_policy_provenance_survives_composition_boundary() -> None:
    candidate_spy = _CandidateEvaluatorSpy()
    result = RotationAssignmentCandidateEvaluationService(
        candidate_service=candidate_spy
    ).evaluate_and_rank(
        build=_build(),
        member_id="char-a",
        assignments=(_assignment(provider=_provider()),),
        policies=(_policy(),),
        candidates=(),
    )

    obligation = result.obligation_projection.obligations[0]
    assert obligation.policy.source == "verified rotation assignment policy"
    assert obligation.assignment.requirement_id == "major_brittle"
