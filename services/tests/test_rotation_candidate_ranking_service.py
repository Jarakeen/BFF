from __future__ import annotations

from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


def _consequence(
    kind: RotationResourceConsequenceKind,
    *,
    minimum: int = 0,
    ending: int = 0,
    cost: int = 0,
    waits: int = 0,
    minimum_fraction_delta: float | None = None,
    ending_fraction_delta: float | None = None,
) -> RotationPlanConsequence:
    return RotationPlanConsequence(
        resource_kind=kind,
        cast_deltas=(),
        cost_deltas=(),
        total_cost_delta=cost,
        minimum_resource_delta=minimum,
        ending_resource_delta=ending,
        shortfall_delta=0,
        wait_delta=waits,
        minimum_resource_fraction_delta=minimum_fraction_delta,
        ending_resource_fraction_delta=ending_fraction_delta,
    )


def _scorecard(
    *,
    consequence: RotationPlanConsequence,
    missing_demand: bool = False,
    missing_effects: tuple[str, ...] = (),
    shortfall: int = 0,
    inherited_unresolved: tuple[str, ...] = (),
    candidate_specific_unresolved: tuple[str, ...] = (),
) -> RotationCandidateScorecard:
    class _Requirement:
        pass

    class _Coverage:
        satisfied = not missing_demand
        requirement = _Requirement()

    return RotationCandidateScorecard(
        consequence=consequence,
        demand_coverage=(_Coverage(),) if missing_demand else (),
        missing_required_effects=missing_effects,
        candidate_shortfall=shortfall,
        inherited_unresolved=inherited_unresolved,
        candidate_specific_unresolved=candidate_specific_unresolved,
    )


def test_eligible_candidate_outranks_resource_improved_candidate_that_misses_hard_obligation() -> None:
    service = RotationCandidateRankingService()
    eligible = _scorecard(
        consequence=_consequence(
            RotationResourceConsequenceKind.WORSENED,
            minimum=-500,
            ending=-500,
            cost=500,
        )
    )
    cheaper_but_missing = _scorecard(
        consequence=_consequence(
            RotationResourceConsequenceKind.IMPROVED,
            minimum=2000,
            ending=2000,
            cost=-2000,
        ),
        missing_demand=True,
    )

    ranked = service.rank(
        (
            RotationCandidateRankingInput("cheap-but-misses-mechanic", cheaper_but_missing),
            RotationCandidateRankingInput("handles-mechanic", eligible),
        )
    )

    assert [item.candidate_id for item in ranked] == [
        "handles-mechanic",
        "cheap-but-misses-mechanic",
    ]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE


def test_shortfall_candidate_cannot_outrank_hard_obligation_candidate_without_shortfall() -> None:
    service = RotationCandidateRankingService()
    safe = _scorecard(
        consequence=_consequence(RotationResourceConsequenceKind.NEUTRAL)
    )
    shortfall = _scorecard(
        consequence=_consequence(
            RotationResourceConsequenceKind.IMPROVED,
            minimum=5000,
            ending=5000,
            cost=-5000,
        ),
        shortfall=1,
    )

    ranked = service.rank(
        (
            RotationCandidateRankingInput("shortfall", shortfall),
            RotationCandidateRankingInput("safe", safe),
        )
    )

    assert [item.candidate_id for item in ranked] == ["safe", "shortfall"]
    assert any("resource shortfall 1" in reason for reason in ranked[1].reasons)


def test_resource_consequence_orders_candidates_only_after_hard_obligations_match() -> None:
    service = RotationCandidateRankingService()
    neutral = _scorecard(
        consequence=_consequence(RotationResourceConsequenceKind.NEUTRAL)
    )
    improved = _scorecard(
        consequence=_consequence(
            RotationResourceConsequenceKind.IMPROVED,
            minimum=1771,
            ending=1771,
            cost=-1771,
        )
    )

    ranked = service.rank(
        (
            RotationCandidateRankingInput("neutral", neutral),
            RotationCandidateRankingInput("improved", improved),
        )
    )

    assert [item.candidate_id for item in ranked] == ["improved", "neutral"]


def test_normalized_resource_floor_breaks_soft_tie_before_raw_amounts() -> None:
    service = RotationCandidateRankingService()
    better_raw_worse_fraction = _scorecard(
        consequence=_consequence(
            RotationResourceConsequenceKind.IMPROVED,
            minimum=1000,
            ending=1000,
            minimum_fraction_delta=0.02,
            ending_fraction_delta=0.02,
        )
    )
    smaller_raw_better_fraction = _scorecard(
        consequence=_consequence(
            RotationResourceConsequenceKind.IMPROVED,
            minimum=500,
            ending=500,
            minimum_fraction_delta=0.05,
            ending_fraction_delta=0.04,
        )
    )

    ranked = service.rank(
        (
            RotationCandidateRankingInput(
                "better-raw-worse-fraction",
                better_raw_worse_fraction,
            ),
            RotationCandidateRankingInput(
                "smaller-raw-better-fraction",
                smaller_raw_better_fraction,
            ),
        )
    )

    assert [item.candidate_id for item in ranked] == [
        "smaller-raw-better-fraction",
        "better-raw-worse-fraction",
    ]
    assert any("normalized resource deltas" in reason for reason in ranked[0].reasons)


def test_candidate_specific_unresolved_counts_but_shared_baseline_limitations_do_not() -> None:
    service = RotationCandidateRankingService()
    shared = ("known baseline limitation",) * 48
    clean = _scorecard(
        consequence=_consequence(RotationResourceConsequenceKind.NEUTRAL),
        inherited_unresolved=shared,
    )
    new_gap = _scorecard(
        consequence=_consequence(RotationResourceConsequenceKind.IMPROVED),
        inherited_unresolved=shared,
        candidate_specific_unresolved=("candidate-only unresolved action",),
    )

    ranked = service.rank(
        (
            RotationCandidateRankingInput("candidate-with-new-gap", new_gap),
            RotationCandidateRankingInput("candidate-with-shared-only", clean),
        )
    )

    assert [item.candidate_id for item in ranked] == [
        "candidate-with-shared-only",
        "candidate-with-new-gap",
    ]
    assert any("candidate-specific" in reason for reason in ranked[1].reasons)
    assert any("inherited/shared" in reason for reason in ranked[0].reasons)


def test_identical_candidates_use_stable_candidate_id_tie_break() -> None:
    service = RotationCandidateRankingService()
    scorecard = _scorecard(
        consequence=_consequence(RotationResourceConsequenceKind.NEUTRAL)
    )

    ranked = service.rank(
        (
            RotationCandidateRankingInput("Zulu", scorecard),
            RotationCandidateRankingInput("alpha", scorecard),
        )
    )

    assert [item.candidate_id for item in ranked] == ["alpha", "Zulu"]


def test_duplicate_candidate_ids_are_rejected_case_insensitively() -> None:
    service = RotationCandidateRankingService()
    scorecard = _scorecard(
        consequence=_consequence(RotationResourceConsequenceKind.NEUTRAL)
    )

    try:
        service.rank(
            (
                RotationCandidateRankingInput("Candidate", scorecard),
                RotationCandidateRankingInput("candidate", scorecard),
            )
        )
    except ValueError as exc:
        assert "duplicate rotation ranking candidate_id" in str(exc)
    else:
        raise AssertionError("expected duplicate candidate ids to be rejected")
