from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_heavy_sustain_ranking_service import (
    RotationCandidateHeavySustainInput,
    RotationCandidateHeavySustainRankingService,
)
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingResult,
    RotationCandidateTier,
)


def _plan(name: str) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(),
        assumptions=(name,),
    )


class _HeavyService:
    def __init__(self, projections):
        self.projections = list(projections)
        self.calls = []

    def project(self, **kwargs):
        self.calls.append(kwargs)
        return self.projections.pop(0)


class _ScorecardService:
    def __init__(self, scorecards):
        self.scorecards = list(scorecards)
        self.calls = []

    def compare(self, **kwargs):
        self.calls.append(kwargs)
        return self.scorecards.pop(0)


class _RankingService:
    def __init__(self, tiers=None, *, drop_last=False):
        self.tiers = tiers or {}
        self.drop_last = drop_last
        self.calls = []

    def rank(self, candidates):
        self.calls.append(candidates)
        values = candidates[:-1] if self.drop_last else candidates
        return tuple(
            RotationCandidateRankingResult(
                candidate_id=item.candidate_id,
                scorecard=item.scorecard,
                tier=self.tiers.get(item.candidate_id, RotationCandidateTier.ELIGIBLE),
                rank=index + 1,
                reasons=(f"ranked {item.candidate_id}",),
            )
            for index, item in enumerate(values)
        )


def _resolved(sustain):
    return SimpleNamespace(sustain_projection=sustain, unresolved=())


def _unresolved(*messages: str):
    return SimpleNamespace(sustain_projection=None, unresolved=tuple(messages))


def test_scorecard_receives_post_heavy_candidate_sustain() -> None:
    post_heavy = object()
    scorecard = SimpleNamespace(label="post-heavy")
    heavy = _HeavyService([_resolved(post_heavy)])
    scorecards = _ScorecardService([scorecard])
    ranking = _RankingService()
    service = RotationCandidateHeavySustainRankingService(
        heavy_service=heavy,
        scorecard_service=scorecards,
        ranking_service=ranking,
    )
    baseline_plan = _plan("baseline")
    baseline_sustain = object()
    candidate_plan = _plan("candidate")

    results = service.evaluate_and_rank(
        character_build=object(),
        sustain_build=object(),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        baseline_plan=baseline_plan,
        baseline_sustain=baseline_sustain,
        candidates=(RotationCandidateHeavySustainInput("candidate", candidate_plan),),
        scorecard_kwargs={"demands": ()},
    )

    assert results[0].tier is RotationCandidateTier.ELIGIBLE
    assert results[0].scorecard is scorecard
    assert scorecards.calls[0]["candidate_sustain"] is post_heavy
    assert scorecards.calls[0]["baseline_sustain"] is baseline_sustain
    assert scorecards.calls[0]["candidate_plan"] is candidate_plan
    assert scorecards.calls[0]["demands"] == ()


def test_unresolved_heavy_evidence_is_hard_ineligible_and_not_scored() -> None:
    heavy = _HeavyService([_unresolved("missing full-charge evidence")])
    scorecards = _ScorecardService([])
    ranking = _RankingService()
    service = RotationCandidateHeavySustainRankingService(
        heavy_service=heavy,
        scorecard_service=scorecards,
        ranking_service=ranking,
    )

    results = service.evaluate_and_rank(
        character_build=object(),
        sustain_build=object(),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        baseline_plan=_plan("baseline"),
        baseline_sustain=object(),
        candidates=(RotationCandidateHeavySustainInput("unknown", _plan("unknown")),),
    )

    assert results[0].tier is RotationCandidateTier.INELIGIBLE
    assert results[0].scorecard is None
    assert "missing full-charge evidence" in results[0].reasons[0]
    assert scorecards.calls == []
    assert ranking.calls == [()]


def test_resolved_generic_hard_failure_remains_ineligible() -> None:
    scorecard = SimpleNamespace(label="known hard failure")
    service = RotationCandidateHeavySustainRankingService(
        heavy_service=_HeavyService([_resolved(object())]),
        scorecard_service=_ScorecardService([scorecard]),
        ranking_service=_RankingService(
            {"failed": RotationCandidateTier.INELIGIBLE}
        ),
    )

    result = service.evaluate_and_rank(
        character_build=object(),
        sustain_build=object(),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        baseline_plan=_plan("baseline"),
        baseline_sustain=object(),
        candidates=(RotationCandidateHeavySustainInput("failed", _plan("failed")),),
    )[0]

    assert result.tier is RotationCandidateTier.INELIGIBLE
    assert result.scorecard is scorecard


def test_resolved_eligible_candidate_ranks_before_unresolved_heavy_candidate() -> None:
    service = RotationCandidateHeavySustainRankingService(
        heavy_service=_HeavyService([
            _unresolved("unknown restore"),
            _resolved(object()),
        ]),
        scorecard_service=_ScorecardService([SimpleNamespace(label="good")]),
        ranking_service=_RankingService(),
    )

    results = service.evaluate_and_rank(
        character_build=object(),
        sustain_build=object(),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        baseline_plan=_plan("baseline"),
        baseline_sustain=object(),
        candidates=(
            RotationCandidateHeavySustainInput("unknown", _plan("unknown")),
            RotationCandidateHeavySustainInput("good", _plan("good")),
        ),
    )

    assert tuple(item.candidate_id for item in results) == ("good", "unknown")
    assert results[0].tier is RotationCandidateTier.ELIGIBLE
    assert results[1].tier is RotationCandidateTier.INELIGIBLE


def test_duplicate_candidate_ids_fail_closed() -> None:
    service = RotationCandidateHeavySustainRankingService(
        heavy_service=_HeavyService([]),
        scorecard_service=_ScorecardService([]),
        ranking_service=_RankingService(),
    )

    with pytest.raises(ValueError, match="duplicate rotation heavy-sustain candidate_id"):
        service.evaluate_and_rank(
            character_build=object(),
            sustain_build=object(),
            resource=ResourceType.MAGICKA,
            initial_bar="front",
            baseline_plan=_plan("baseline"),
            baseline_sustain=object(),
            candidates=(
                RotationCandidateHeavySustainInput("Same", _plan("a")),
                RotationCandidateHeavySustainInput("same", _plan("b")),
            ),
        )


def test_managed_scorecard_arguments_cannot_be_overridden() -> None:
    service = RotationCandidateHeavySustainRankingService(
        heavy_service=_HeavyService([]),
        scorecard_service=_ScorecardService([]),
        ranking_service=_RankingService(),
    )

    with pytest.raises(ValueError, match="cannot override managed argument"):
        service.evaluate_and_rank(
            character_build=object(),
            sustain_build=object(),
            resource=ResourceType.MAGICKA,
            initial_bar="front",
            baseline_plan=_plan("baseline"),
            baseline_sustain=object(),
            candidates=(RotationCandidateHeavySustainInput("candidate", _plan("candidate")),),
            scorecard_kwargs={"candidate_sustain": object()},
        )


def test_ranking_must_return_same_resolved_candidate_set() -> None:
    service = RotationCandidateHeavySustainRankingService(
        heavy_service=_HeavyService([_resolved(object())]),
        scorecard_service=_ScorecardService([SimpleNamespace(label="score")]),
        ranking_service=_RankingService(drop_last=True),
    )

    with pytest.raises(ValueError, match="different resolved candidate set"):
        service.evaluate_and_rank(
            character_build=object(),
            sustain_build=object(),
            resource=ResourceType.MAGICKA,
            initial_bar="front",
            baseline_plan=_plan("baseline"),
            baseline_sustain=object(),
            candidates=(RotationCandidateHeavySustainInput("candidate", _plan("candidate")),),
        )
