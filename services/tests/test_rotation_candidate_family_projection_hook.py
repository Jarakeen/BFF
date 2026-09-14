from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_family_recommendation_service import (
    RotationCandidateFamilyRecommendationService,
    RotationCandidateRoleEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_ranking_service import RotationCandidateTier


class _FakeGenerationService:
    def __init__(self, candidates):
        self.candidates = tuple(candidates)

    def generate(self, **_kwargs):
        return self.candidates


class _FakeRankingService:
    def rank(self, inputs):
        return tuple(
            SimpleNamespace(
                candidate_id=item.candidate_id,
                tier=RotationCandidateTier.ELIGIBLE,
                base_ranking=SimpleNamespace(reasons=()),
                role_reasons=(),
            )
            for item in inputs
        )


def _candidate(candidate_id: str) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Tank",
            build_name="Main Tank",
            duration_seconds=20.0,
            actions=(),
        ),
        refresh_leads=(),
    )


def test_family_projector_runs_before_baseline_and_candidate_evaluation() -> None:
    candidates = (_candidate("baseline"), _candidate("sibling"))
    projected_ids = []
    evaluated = []

    def projector(candidate):
        projected_ids.append(candidate.candidate_id)
        plan = RotationPlan(
            character_name=candidate.plan.character_name,
            build_name=candidate.plan.build_name,
            duration_seconds=candidate.plan.duration_seconds,
            actions=candidate.plan.actions
            + (
                RotationAction(
                    time_seconds=5.0,
                    sequence=0,
                    kind=RotationActionKind.BLOCK,
                ),
            ),
            assumptions=candidate.plan.assumptions,
            unresolved=candidate.plan.unresolved,
        )
        return GeneratedRotationCandidate(
            candidate_id=candidate.candidate_id,
            plan=plan,
            refresh_leads=candidate.refresh_leads,
            action_claims=candidate.action_claims,
        )

    def evaluator(candidate, baseline):
        evaluated.append(
            (
                candidate.candidate_id,
                candidate.plan.actions[0].kind,
                baseline.plan.actions[0].kind,
            )
        )
        return RotationCandidateRoleEvidence(
            scorecard=object(),
            role_output_value=1.0,
            assigned_support_value=1.0,
            sustain_margin=1.0,
            primary_role_displacement_seconds=0.0,
        )

    result = RotationCandidateFamilyRecommendationService(
        generation_service=_FakeGenerationService(candidates),
        ranking_service=_FakeRankingService(),
    ).recommend(
        seed_plan=object(),
        priorities=object(),
        evaluator=evaluator,
        role_key="tank",
        role_output_label="tank output",
        assigned_support_label="assigned support",
        candidate_projector=projector,
    )

    assert projected_ids == ["baseline", "sibling"]
    assert evaluated == [
        ("baseline", RotationActionKind.BLOCK, RotationActionKind.BLOCK),
        ("sibling", RotationActionKind.BLOCK, RotationActionKind.BLOCK),
    ]
    assert result.recommended is not None


def test_family_projector_must_preserve_candidate_identity() -> None:
    candidate = _candidate("baseline")

    def projector(value):
        return GeneratedRotationCandidate(
            candidate_id="different",
            plan=value.plan,
            refresh_leads=value.refresh_leads,
            action_claims=value.action_claims,
        )

    with pytest.raises(ValueError, match="preserve candidate identity"):
        RotationCandidateFamilyRecommendationService(
            generation_service=_FakeGenerationService((candidate,)),
            ranking_service=_FakeRankingService(),
        ).recommend(
            seed_plan=object(),
            priorities=object(),
            evaluator=lambda *_args: None,
            role_key="tank",
            role_output_label="tank output",
            assigned_support_label="assigned support",
            candidate_projector=projector,
        )


def test_family_projector_must_return_generated_candidate() -> None:
    candidate = _candidate("baseline")

    with pytest.raises(TypeError, match="must return GeneratedRotationCandidate"):
        RotationCandidateFamilyRecommendationService(
            generation_service=_FakeGenerationService((candidate,)),
            ranking_service=_FakeRankingService(),
        ).recommend(
            seed_plan=object(),
            priorities=object(),
            evaluator=lambda *_args: None,
            role_key="tank",
            role_output_label="tank output",
            assigned_support_label="assigned support",
            candidate_projector=lambda _candidate: object(),
        )
