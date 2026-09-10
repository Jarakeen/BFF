from services.rotation_candidate_family_recommendation_service import (
    RotationCandidateFamilyRecommendationService,
    RotationCandidateRoleEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


def _consequence() -> RotationPlanConsequence:
    return RotationPlanConsequence(
        resource_kind=RotationResourceConsequenceKind.NEUTRAL,
        cast_deltas=(),
        cost_deltas=(),
        total_cost_delta=0,
        minimum_resource_delta=0,
        ending_resource_delta=0,
        shortfall_delta=0,
        wait_delta=0,
    )


def _scorecard(
    *,
    missing_effects: tuple[str, ...] = (),
    shortfall: int = 0,
    inherited_unresolved: tuple[str, ...] = (),
    candidate_unresolved: tuple[str, ...] = (),
) -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(),
        missing_required_effects=missing_effects,
        candidate_shortfall=shortfall,
        inherited_unresolved=inherited_unresolved,
        candidate_specific_unresolved=candidate_unresolved,
    )


class _FakeGenerationService:
    def __init__(self, candidates):
        self.candidates = tuple(candidates)
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.candidates


def _candidate(candidate_id: str, *, claims=()) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=object(),
        refresh_leads=(),
        action_claims=tuple(claims),
    )


def test_recommend_runs_whole_family_against_same_baseline_and_forwards_claims() -> None:
    claim = object()
    baseline = _candidate("baseline", claims=(claim,))
    high_damage = _candidate("high-damage", claims=(claim,))
    safe_damage = _candidate("safe-damage", claims=(claim,))
    generation = _FakeGenerationService((baseline, high_damage, safe_damage))
    evaluated = []

    def evaluate(candidate, family_baseline):
        evaluated.append((candidate.candidate_id, family_baseline.candidate_id))
        output = {
            "baseline": 100_000.0,
            "high-damage": 130_000.0,
            "safe-damage": 120_000.0,
        }[candidate.candidate_id]
        return RotationCandidateRoleEvidence(
            scorecard=_scorecard(),
            role_output_value=output,
            assigned_support_value=0.0,
            sustain_margin=1000.0,
            primary_role_displacement_seconds=0.0,
        )

    result = RotationCandidateFamilyRecommendationService(
        generation_service=generation,
    ).recommend(
        seed_plan=object(),
        priorities=object(),
        evaluator=evaluate,
        role_key="dd",
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
        action_claims=(claim,),
    )

    assert generation.calls[0]["action_claims"] == (claim,)
    assert evaluated == [
        ("baseline", "baseline"),
        ("high-damage", "baseline"),
        ("safe-damage", "baseline"),
    ]
    assert [entry.candidate.candidate_id for entry in result.entries] == [
        "high-damage",
        "safe-damage",
        "baseline",
    ]
    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "high-damage"
    assert "effective damage=130000" in result.recommended.reasons[-3]


def test_hard_invalid_dd_cannot_win_family_recommendation_with_huge_output() -> None:
    candidates = (_candidate("valid"), _candidate("invalid-huge-output"))
    generation = _FakeGenerationService(candidates)

    def evaluate(candidate, _baseline):
        invalid = candidate.candidate_id == "invalid-huge-output"
        return RotationCandidateRoleEvidence(
            scorecard=_scorecard(
                missing_effects=("major_brittle",) if invalid else (),
            ),
            role_output_value=250_000.0 if invalid else 110_000.0,
            assigned_support_value=0.0,
            sustain_margin=1000.0,
            primary_role_displacement_seconds=0.0,
        )

    result = RotationCandidateFamilyRecommendationService(
        generation_service=generation,
    ).recommend(
        seed_plan=object(),
        priorities=object(),
        evaluator=evaluate,
        role_key="dps",
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "valid"
    assert result.entries[1].ranking.tier.value == "ineligible"
    assert "missing static required effect(s): major_brittle" in result.entries[1].reasons


def test_support_family_prefers_assigned_support_before_optional_output() -> None:
    candidates = (_candidate("damage-ish"), _candidate("assignment-first"))
    generation = _FakeGenerationService(candidates)

    def evaluate(candidate, _baseline):
        assignment_first = candidate.candidate_id == "assignment-first"
        return RotationCandidateRoleEvidence(
            scorecard=_scorecard(),
            role_output_value=1000.0 if assignment_first else 9000.0,
            assigned_support_value=0.99 if assignment_first else 0.92,
            sustain_margin=1000.0,
            primary_role_displacement_seconds=0.0,
        )

    result = RotationCandidateFamilyRecommendationService(
        generation_service=generation,
    ).recommend(
        seed_plan=object(),
        priorities=object(),
        evaluator=evaluate,
        role_key="healer",
        role_output_label="useful damage",
        assigned_support_label="assigned support coverage",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "assignment-first"
    assert "assigned support coverage=0.99" in result.recommended.reasons[-3]


def test_all_invalid_candidates_fail_closed_without_recommending_least_bad_plan() -> None:
    candidates = (_candidate("missing-job"), _candidate("resource-failure"))
    generation = _FakeGenerationService(candidates)

    def evaluate(candidate, _baseline):
        return RotationCandidateRoleEvidence(
            scorecard=(
                _scorecard(missing_effects=("required_effect",))
                if candidate.candidate_id == "missing-job"
                else _scorecard(shortfall=1)
            ),
            role_output_value=999_999.0,
            assigned_support_value=999.0,
            sustain_margin=9999.0,
            primary_role_displacement_seconds=0.0,
        )

    result = RotationCandidateFamilyRecommendationService(
        generation_service=generation,
    ).recommend(
        seed_plan=object(),
        priorities=object(),
        evaluator=evaluate,
        role_key="tank",
        role_output_label="useful damage",
        assigned_support_label="assigned support coverage",
    )

    assert result.entries
    assert all(entry.ranking.tier.value == "ineligible" for entry in result.entries)
    assert result.recommended is None
    assert not result.has_recommendation


def test_candidate_specific_unresolved_blocks_but_shared_unresolved_stays_diagnostic() -> None:
    candidates = (_candidate("shared-limitation"), _candidate("candidate-unknown"))
    generation = _FakeGenerationService(candidates)

    def evaluate(candidate, _baseline):
        return RotationCandidateRoleEvidence(
            scorecard=(
                _scorecard(inherited_unresolved=("shared duration evidence missing",))
                if candidate.candidate_id == "shared-limitation"
                else _scorecard(candidate_unresolved=("candidate proc timing unknown",))
            ),
            role_output_value=100_000.0,
            assigned_support_value=0.0,
            sustain_margin=1000.0,
            primary_role_displacement_seconds=0.0,
        )

    result = RotationCandidateFamilyRecommendationService(
        generation_service=generation,
    ).recommend(
        seed_plan=object(),
        priorities=object(),
        evaluator=evaluate,
        role_key="dd",
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "shared-limitation"
    assert result.entries[0].ranking.tier.value == "eligible"
    assert result.entries[1].ranking.tier.value == "ineligible"


def test_exact_family_tie_remains_deterministic() -> None:
    candidates = (_candidate("Zulu"), _candidate("alpha"))
    generation = _FakeGenerationService(candidates)

    def evaluate(_candidate_value, _baseline):
        return RotationCandidateRoleEvidence(
            scorecard=_scorecard(),
            role_output_value=1000.0,
            assigned_support_value=1.0,
            sustain_margin=1000.0,
            primary_role_displacement_seconds=0.0,
        )

    result = RotationCandidateFamilyRecommendationService(
        generation_service=generation,
    ).recommend(
        seed_plan=object(),
        priorities=object(),
        evaluator=evaluate,
        role_key="healer",
        role_output_label="useful damage",
        assigned_support_label="assigned support coverage",
    )

    assert [entry.candidate.candidate_id for entry in result.entries] == ["alpha", "Zulu"]
    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "alpha"
