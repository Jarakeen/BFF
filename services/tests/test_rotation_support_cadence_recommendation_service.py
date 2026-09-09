from types import SimpleNamespace

import pytest

from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_support_cadence_recommendation_service import (
    RotationSupportCadenceRecommendationService,
)


def _evaluated(candidate_id: str, rationale: str = "cadence rationale"):
    return SimpleNamespace(candidate_id=candidate_id, rationale=rationale)


def _ranking(
    candidate_id: str,
    *,
    rank: int,
    tier: RotationCandidateTier = RotationCandidateTier.ELIGIBLE,
    reasons: tuple[str, ...] = (),
):
    return SimpleNamespace(
        candidate_id=candidate_id,
        rank=rank,
        tier=tier,
        reasons=reasons,
    )


def test_recommends_first_eligible_ranked_candidate_and_preserves_evidence() -> None:
    evaluated = (
        _evaluated("major_slayer:combat_prayer:full", "full coverage"),
        _evaluated("major_slayer:combat_prayer:target", "target floor"),
    )
    ranking = (
        _ranking(
            "major_slayer:combat_prayer:target",
            rank=1,
            reasons=("resource consequence improved",),
        ),
        _ranking("major_slayer:combat_prayer:full", rank=2),
    )

    result = RotationSupportCadenceRecommendationService().recommend(
        evaluated=evaluated,
        ranking=ranking,
    )

    assert [item.candidate_id for item in result.ordered] == [
        "major_slayer:combat_prayer:target",
        "major_slayer:combat_prayer:full",
    ]
    assert result.recommended is result.ordered[0]
    assert result.recommended.rationale == "target floor"
    assert result.recommended.reasons == ("resource consequence improved",)
    assert result.has_eligible_candidate is True


def test_skips_ineligible_rank_one_and_recommends_first_eligible_result() -> None:
    evaluated = (_evaluated("a"), _evaluated("b"))
    ranking = (
        _ranking("a", rank=1, tier=RotationCandidateTier.INELIGIBLE),
        _ranking("b", rank=2, tier=RotationCandidateTier.ELIGIBLE),
    )

    result = RotationSupportCadenceRecommendationService().recommend(
        evaluated=evaluated,
        ranking=ranking,
    )

    assert result.recommended is not None
    assert result.recommended.candidate_id == "b"


def test_all_ineligible_candidates_produce_no_recommendation() -> None:
    result = RotationSupportCadenceRecommendationService().recommend(
        evaluated=(_evaluated("a"), _evaluated("b")),
        ranking=(
            _ranking("a", rank=1, tier=RotationCandidateTier.INELIGIBLE),
            _ranking("b", rank=2, tier=RotationCandidateTier.INELIGIBLE),
        ),
    )

    assert result.recommended is None
    assert result.has_eligible_candidate is False
    assert len(result.ordered) == 2


def test_ranking_must_exactly_match_evaluated_candidate_set() -> None:
    with pytest.raises(ValueError, match="exactly match"):
        RotationSupportCadenceRecommendationService().recommend(
            evaluated=(_evaluated("a"), _evaluated("b")),
            ranking=(_ranking("a", rank=1),),
        )


def test_ranking_must_be_contiguous_and_in_rank_order() -> None:
    with pytest.raises(ValueError, match="contiguous rank order"):
        RotationSupportCadenceRecommendationService().recommend(
            evaluated=(_evaluated("a"), _evaluated("b")),
            ranking=(
                _ranking("a", rank=2),
                _ranking("b", rank=1),
            ),
        )


def test_empty_candidate_set_returns_empty_recommendation() -> None:
    result = RotationSupportCadenceRecommendationService().recommend(
        evaluated=(),
        ranking=(),
    )

    assert result.ordered == ()
    assert result.recommended is None
