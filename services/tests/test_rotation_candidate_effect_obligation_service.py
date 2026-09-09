from __future__ import annotations

from dataclasses import dataclass

import pytest

from services.rotation_candidate_effect_obligation_service import (
    RotationCandidateEffectObligationService,
    RotationEffectObligationCandidate,
)
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingResult,
    RotationCandidateTier,
)
from services.rotation_effect_uptime_service import (
    RotationEffectUptimeAssessment,
    RotationEffectUptimeRequirement,
    RotationEffectUptimeSummary,
)


@dataclass
class _ScorecardStub:
    name: str


class _FakeBaseRanker:
    def __init__(self, ordering: tuple[tuple[str, RotationCandidateTier], ...]) -> None:
        self.ordering = ordering

    def rank(self, candidates: tuple[RotationCandidateRankingInput, ...]):
        by_id = {candidate.candidate_id: candidate for candidate in candidates}
        return tuple(
            RotationCandidateRankingResult(
                candidate_id=candidate_id,
                scorecard=by_id.get(candidate_id, _input(candidate_id)).scorecard,
                tier=tier,
                rank=index + 1,
                reasons=(f"base {candidate_id}",),
            )
            for index, (candidate_id, tier) in enumerate(self.ordering)
        )


def _input(candidate_id: str) -> RotationCandidateRankingInput:
    return RotationCandidateRankingInput(
        candidate_id=candidate_id,
        scorecard=_ScorecardStub(candidate_id),
    )


def _assessment(
    *,
    uptime: float | None,
    minimum: float = 0.90,
    effect: str = "chilled",
    source: str = "Winter's Revenge",
    bar: str = "back",
) -> RotationEffectUptimeAssessment:
    requirement = RotationEffectUptimeRequirement(
        effect_name=effect,
        source_skill_name=source,
        minimum_uptime=minimum,
        bar=bar,
    )
    if uptime is None:
        return RotationEffectUptimeAssessment(
            requirement=requirement,
            summary=None,
            unresolved=("verified effect duration unavailable",),
        )
    return RotationEffectUptimeAssessment(
        requirement=requirement,
        summary=RotationEffectUptimeSummary(
            effect_name=effect,
            source_skill_name=source,
            bar=bar,
            base_duration_seconds=4.0,
            effective_duration_seconds=20.0,
            cast_count=3,
            active_seconds=60.0 * uptime,
            uptime_fraction=uptime,
            applied_modifier_sources=("Serpent's Disdain (5)",),
        ),
    )


def test_effect_uptime_failure_makes_otherwise_eligible_candidate_ineligible() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((
            ("more-magicka", RotationCandidateTier.ELIGIBLE),
            ("meets-effect", RotationCandidateTier.ELIGIBLE),
        ))
    )

    ranked = service.rank((
        RotationEffectObligationCandidate(
            _input("more-magicka"),
            (_assessment(uptime=0.80),),
        ),
        RotationEffectObligationCandidate(
            _input("meets-effect"),
            (_assessment(uptime=0.95),),
        ),
    ))

    assert [item.candidate_id for item in ranked] == ["meets-effect", "more-magicka"]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("observed 80.00%, required 90.00%" in reason for reason in ranked[1].reasons)


def test_missing_effect_uptime_evidence_fails_closed() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((("unknown", RotationCandidateTier.ELIGIBLE),))
    )

    ranked = service.rank((
        RotationEffectObligationCandidate(
            _input("unknown"),
            (_assessment(uptime=None),),
        ),
    ))

    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert ranked[0].failed_effect_uptime_assessments[0].observed_uptime is None
    assert any("verified effect duration unavailable" in reason for reason in ranked[0].reasons)


def test_base_hard_failure_remains_ineligible_even_when_effect_uptime_passes() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((("base-failure", RotationCandidateTier.INELIGIBLE),))
    )

    ranked = service.rank((
        RotationEffectObligationCandidate(
            _input("base-failure"),
            (_assessment(uptime=1.0),),
        ),
    ))

    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert ranked[0].failed_effect_uptime_assessments == ()


def test_no_effect_requirements_preserves_existing_base_order() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((
            ("first", RotationCandidateTier.ELIGIBLE),
            ("second", RotationCandidateTier.ELIGIBLE),
        ))
    )

    ranked = service.rank((
        RotationEffectObligationCandidate(_input("first")),
        RotationEffectObligationCandidate(_input("second")),
    ))

    assert [item.candidate_id for item in ranked] == ["first", "second"]
    assert [item.rank for item in ranked] == [1, 2]


def test_pareto_superior_uptime_beats_better_base_rank_after_both_meet_floor() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((
            ("base-favorite", RotationCandidateTier.ELIGIBLE),
            ("uptime-better", RotationCandidateTier.ELIGIBLE),
        ))
    )

    ranked = service.rank((
        RotationEffectObligationCandidate(
            _input("base-favorite"),
            (
                _assessment(uptime=0.92, effect="minor_courage", source="Combat Prayer", bar="front"),
                _assessment(uptime=0.93, effect="major_resolve", source="Expansive Frost Cloak", bar="back"),
            ),
        ),
        RotationEffectObligationCandidate(
            _input("uptime-better"),
            (
                _assessment(uptime=0.98, effect="minor_courage", source="Combat Prayer", bar="front"),
                _assessment(uptime=0.97, effect="major_resolve", source="Expansive Frost Cloak", bar="back"),
            ),
        ),
    ))

    assert [item.candidate_id for item in ranked] == ["uptime-better", "base-favorite"]
    assert all(item.tier is RotationCandidateTier.ELIGIBLE for item in ranked)
    assert any(
        "Pareto-dominated by uptime-better" in reason
        for reason in ranked[1].reasons
    )


def test_incomparable_effect_uptime_tradeoff_preserves_base_order() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((
            ("courage-heavy", RotationCandidateTier.ELIGIBLE),
            ("resolve-heavy", RotationCandidateTier.ELIGIBLE),
        ))
    )

    ranked = service.rank((
        RotationEffectObligationCandidate(
            _input("courage-heavy"),
            (
                _assessment(uptime=0.99, effect="minor_courage", source="Combat Prayer", bar="front"),
                _assessment(uptime=0.92, effect="major_resolve", source="Expansive Frost Cloak", bar="back"),
            ),
        ),
        RotationEffectObligationCandidate(
            _input("resolve-heavy"),
            (
                _assessment(uptime=0.94, effect="minor_courage", source="Combat Prayer", bar="front"),
                _assessment(uptime=0.99, effect="major_resolve", source="Expansive Frost Cloak", bar="back"),
            ),
        ),
    ))

    assert [item.candidate_id for item in ranked] == ["courage-heavy", "resolve-heavy"]
    assert not any("Pareto-dominated" in reason for item in ranked for reason in item.reasons)


def test_effect_uptime_candidates_require_same_explicit_requirement_set() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((
            ("one", RotationCandidateTier.ELIGIBLE),
            ("two", RotationCandidateTier.ELIGIBLE),
        ))
    )

    with pytest.raises(ValueError, match="same explicit requirement set"):
        service.rank((
            RotationEffectObligationCandidate(
                _input("one"),
                (_assessment(uptime=0.95, effect="minor_courage", source="Combat Prayer", bar="front"),),
            ),
            RotationEffectObligationCandidate(
                _input("two"),
                (_assessment(uptime=0.95, effect="major_resolve", source="Expansive Frost Cloak", bar="back"),),
            ),
        ))


def test_duplicate_candidate_ids_fail_closed() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((("same", RotationCandidateTier.ELIGIBLE),))
    )

    with pytest.raises(ValueError, match="duplicate rotation effect-obligation candidate_id"):
        service.rank((
            RotationEffectObligationCandidate(_input("same")),
            RotationEffectObligationCandidate(_input("same")),
        ))


def test_duplicate_effect_assessments_for_one_candidate_fail_closed() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((("candidate", RotationCandidateTier.ELIGIBLE),))
    )
    assessment = _assessment(uptime=0.95)

    with pytest.raises(ValueError, match="duplicate effect uptime assessment"):
        service.rank((
            RotationEffectObligationCandidate(
                _input("candidate"),
                (assessment, assessment),
            ),
        ))


def test_semantic_duplicate_skill_identity_fails_closed() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((("candidate", RotationCandidateTier.ELIGIBLE),))
    )

    with pytest.raises(ValueError, match="duplicate effect uptime assessment"):
        service.rank((
            RotationEffectObligationCandidate(
                _input("candidate"),
                (
                    _assessment(uptime=0.95, source="Winter's Revenge"),
                    _assessment(uptime=0.95, source="Winters Revenge"),
                ),
            ),
        ))


def test_base_ranker_must_return_same_candidate_set() -> None:
    service = RotationCandidateEffectObligationService(
        _FakeBaseRanker((("different", RotationCandidateTier.ELIGIBLE),))
    )

    with pytest.raises(ValueError, match="same candidate set"):
        service.rank((RotationEffectObligationCandidate(_input("candidate")),))
