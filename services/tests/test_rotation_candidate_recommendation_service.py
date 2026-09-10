import pytest

from minmax.demand_action_claim_duration_scheduler import DemandActionClaim
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_recommendation_service import (
    RotationCandidateRecommendationEvidence,
    RotationCandidateRecommendationService,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


def _plan(name: str) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name=name,
        duration_seconds=20.0,
        actions=(),
    )


def _candidate(
    candidate_id: str,
    *,
    claims: tuple[DemandActionClaim, ...] = (),
) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=_plan(candidate_id),
        refresh_leads=(),
        action_claims=claims,
    )


def _scorecard(*, missing_effects: tuple[str, ...] = (), shortfall: int = 0):
    return RotationCandidateScorecard(
        consequence=RotationPlanConsequence(
            resource_kind=RotationResourceConsequenceKind.NEUTRAL,
            cast_deltas=(),
            cost_deltas=(),
            total_cost_delta=0,
            minimum_resource_delta=0,
            ending_resource_delta=0,
            shortfall_delta=0,
            wait_delta=0,
        ),
        demand_coverage=(),
        missing_required_effects=missing_effects,
        candidate_shortfall=shortfall,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def _evidence(
    candidate_id: str,
    *,
    output: float | None,
    support: float | None,
    sustain: float | None = 1000.0,
    displacement: float | None = 0.0,
    scorecard: RotationCandidateScorecard | None = None,
) -> RotationCandidateRecommendationEvidence:
    return RotationCandidateRecommendationEvidence(
        candidate_id=candidate_id,
        scorecard=scorecard or _scorecard(),
        role_output_value=output,
        assigned_support_value=support,
        sustain_margin=sustain,
        primary_role_displacement_seconds=displacement,
    )


class _EvidenceProvider:
    def __init__(self, evidence_by_id):
        self.evidence_by_id = evidence_by_id
        self.calls = []

    def evaluate(self, *, baseline, candidate):
        self.calls.append((baseline.candidate_id, candidate.candidate_id))
        return self.evidence_by_id[candidate.candidate_id]


class _GenerationService:
    def __init__(self, candidates):
        self.candidates = tuple(candidates)
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.candidates


def _recommend(service, candidates, provider, *, role="dd"):
    return service.recommend(
        candidates=tuple(candidates),
        evidence_provider=provider,
        role_key=role,
        role_output_label="effective damage" if role == "dd" else "useful output",
        assigned_support_label="assigned support coverage",
    )


def test_recommendation_orchestrates_hard_validity_before_dd_output() -> None:
    candidates = (
        _candidate("baseline"),
        _candidate("huge-output-misses-job"),
        _candidate("valid-output"),
    )
    provider = _EvidenceProvider(
        {
            "baseline": _evidence("baseline", output=100_000, support=None),
            "huge-output-misses-job": _evidence(
                "huge-output-misses-job",
                output=250_000,
                support=None,
                scorecard=_scorecard(missing_effects=("major_brittle",)),
            ),
            "valid-output": _evidence("valid-output", output=125_000, support=None),
        }
    )

    result = _recommend(RotationCandidateRecommendationService(), candidates, provider)

    assert result.has_recommendation
    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "valid-output"
    assert [entry.candidate.candidate_id for entry in result.entries] == [
        "valid-output",
        "baseline",
        "huge-output-misses-job",
    ]
    losing_reasons = result.entries[-1].reasons
    assert any("missing static required effect" in reason for reason in losing_reasons)
    assert any("DD policy" in reason for reason in result.recommended.reasons)
    assert provider.calls == [
        ("baseline", "baseline"),
        ("baseline", "huge-output-misses-job"),
        ("baseline", "valid-output"),
    ]


def test_support_recommendation_uses_assigned_support_before_optional_output() -> None:
    candidates = (_candidate("more-output"), _candidate("better-support"))
    provider = _EvidenceProvider(
        {
            "more-output": _evidence("more-output", output=9000, support=0.92),
            "better-support": _evidence("better-support", output=1000, support=0.99),
        }
    )

    result = _recommend(
        RotationCandidateRecommendationService(),
        candidates,
        provider,
        role="healer",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "better-support"
    assert "assigned support coverage=0.99" in result.recommended.ranking.role_reasons[0]


def test_no_ineligible_candidate_is_mislabeled_as_a_recommendation() -> None:
    candidates = (_candidate("missing-job"), _candidate("resource-fail"))
    provider = _EvidenceProvider(
        {
            "missing-job": _evidence(
                "missing-job",
                output=200_000,
                support=None,
                scorecard=_scorecard(missing_effects=("required_effect",)),
            ),
            "resource-fail": _evidence(
                "resource-fail",
                output=300_000,
                support=None,
                scorecard=_scorecard(shortfall=1),
            ),
        }
    )

    result = _recommend(RotationCandidateRecommendationService(), candidates, provider)

    assert not result.has_recommendation
    assert result.recommended is None
    assert result.best_available is not None
    assert result.best_available.ranking.tier.value == "ineligible"


def test_missing_role_critical_evidence_fails_closed_at_recommendation_boundary() -> None:
    candidates = (_candidate("unknown-output"), _candidate("proven-output"))
    provider = _EvidenceProvider(
        {
            "unknown-output": _evidence("unknown-output", output=None, support=None),
            "proven-output": _evidence("proven-output", output=100_000, support=None),
        }
    )

    result = _recommend(RotationCandidateRecommendationService(), candidates, provider)

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "proven-output"
    unknown = next(
        entry for entry in result.entries if entry.candidate.candidate_id == "unknown-output"
    )
    assert unknown.ranking.tier.value == "ineligible"
    assert "role ranking evidence missing: role output" in unknown.ranking.role_reasons


def test_candidate_evidence_identity_mismatch_fails_explicitly() -> None:
    provider = _EvidenceProvider(
        {"baseline": _evidence("some-other-candidate", output=100_000, support=None)}
    )

    with pytest.raises(ValueError, match="evidence candidate mismatch"):
        _recommend(
            RotationCandidateRecommendationService(),
            (_candidate("baseline"),),
            provider,
        )


def test_duplicate_candidate_identity_fails_before_evaluation() -> None:
    provider = _EvidenceProvider({"same": _evidence("same", output=100_000, support=None)})

    with pytest.raises(ValueError, match="duplicate rotation recommendation candidate_id"):
        _recommend(
            RotationCandidateRecommendationService(),
            (_candidate("same"), _candidate("SAME")),
            provider,
        )

    assert provider.calls == []


def test_generate_and_recommend_preserves_shared_encounter_action_claims() -> None:
    claim = DemandActionClaim(
        demand_name="portal burst",
        bar="front",
        skill_name="combat_prayer",
    )
    candidates = (
        _candidate("baseline", claims=(claim,)),
        _candidate("early-refresh", claims=(claim,)),
    )
    generation = _GenerationService(candidates)
    provider = _EvidenceProvider(
        {
            "baseline": _evidence("baseline", output=100_000, support=None),
            "early-refresh": _evidence("early-refresh", output=110_000, support=None),
        }
    )
    service = RotationCandidateRecommendationService(generation_service=generation)
    seed_plan = _plan("seed")
    priorities = object()

    result = service.generate_and_recommend(
        evidence_provider=provider,
        role_key="dd",
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
        seed_plan=seed_plan,
        priorities=priorities,
        action_claims=(claim,),
    )

    assert generation.calls[0]["action_claims"] == (claim,)
    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "early-refresh"
    assert all(entry.candidate.action_claims == (claim,) for entry in result.entries)


def test_empty_candidate_family_returns_no_recommendation_without_evaluation() -> None:
    provider = _EvidenceProvider({})

    result = _recommend(RotationCandidateRecommendationService(), (), provider)

    assert result.entries == ()
    assert result.recommended is None
    assert result.best_available is None
    assert provider.calls == []
