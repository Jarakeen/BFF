from __future__ import annotations

from dataclasses import dataclass

import pytest

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearSlot
from minmax.role import Role
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_effect_evaluation_service import (
    RotationCandidateEffectEvaluationInput,
    RotationCandidateEffectEvaluationService,
)
from services.rotation_candidate_effect_obligation_service import RotationCandidateEffectObligationService
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingResult,
    RotationCandidateTier,
)
from services.rotation_candidate_temporal_effect_service import (
    RotationCandidateTemporalEffectInput,
    RotationCandidateTemporalEffectService,
)
from services.rotation_temporal_effect_uptime_service import (
    RotationTemporalEffectApplication,
    RotationTemporalEffectRequirement,
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
                scorecard=by_id[candidate_id].scorecard,
                tier=tier,
                rank=index + 1,
                reasons=(f"base {candidate_id}",),
            )
            for index, (candidate_id, tier) in enumerate(self.ordering)
        )


def _build(*, include_proc: bool = True) -> CharacterBuild:
    proc = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Test Set (5)",
        duration=10.0,
    )
    return CharacterBuild(
        name="Temporal Candidate Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=(
            ArmorPiece(
                slot=GearSlot.CHEST,
                effects=(proc,),
            ),
        ) if include_proc else (),
    )


def _generated(candidate_id: str) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Magrat",
            build_name="Temporal Candidate Build",
            duration_seconds=40.0,
            actions=(),
        ),
        refresh_leads=(),
    )


def _ranking_input(candidate_id: str) -> RotationCandidateRankingInput:
    return RotationCandidateRankingInput(
        candidate_id=candidate_id,
        scorecard=_ScorecardStub(candidate_id),
    )


def _effect_ranked(
    build: CharacterBuild,
    ordering: tuple[tuple[str, RotationCandidateTier], ...],
):
    service = RotationCandidateEffectEvaluationService(
        obligation_service=RotationCandidateEffectObligationService(_FakeBaseRanker(ordering))
    )
    candidates = tuple(
        RotationCandidateEffectEvaluationInput(
            generated_candidate=_generated(candidate_id),
            ranking_input=_ranking_input(candidate_id),
        )
        for candidate_id, _tier in ordering
    )
    return service.evaluate_and_rank(build=build, candidates=candidates)


def _requirement() -> RotationTemporalEffectRequirement:
    return RotationTemporalEffectRequirement(
        effect_name="major_slayer",
        layer=EffectLayer.PROC,
        minimum_uptime=0.50,
        source="Test Set (5)",
    )


def _application(time_seconds: float) -> RotationTemporalEffectApplication:
    return RotationTemporalEffectApplication(
        time_seconds=time_seconds,
        effect_name="major_slayer",
        layer=EffectLayer.PROC,
        source="Test Set (5)",
        bar="front",
    )


def test_temporal_failure_demotes_otherwise_eligible_candidate() -> None:
    build = _build()
    effect_ranked = _effect_ranked(
        build,
        (
            ("better-base", RotationCandidateTier.ELIGIBLE),
            ("meets-proc", RotationCandidateTier.ELIGIBLE),
        ),
    )
    by_id = {item.candidate_id: item for item in effect_ranked}

    ranked = RotationCandidateTemporalEffectService().evaluate_and_rank(
        build=build,
        candidates=(
            RotationCandidateTemporalEffectInput(
                by_id["better-base"],
                applications=(_application(0.0),),
            ),
            RotationCandidateTemporalEffectInput(
                by_id["meets-proc"],
                applications=(_application(0.0), _application(20.0)),
            ),
        ),
        requirements=(_requirement(),),
    )

    assert [item.candidate_id for item in ranked] == ["meets-proc", "better-base"]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert ranked[0].temporal_assessments[0].observed_uptime == pytest.approx(0.50)
    assert ranked[1].temporal_assessments[0].observed_uptime == pytest.approx(0.25)
    assert any("observed 25.00%, required 50.00%" in reason for reason in ranked[1].reasons)


def test_upstream_hard_failure_remains_ineligible_when_temporal_requirement_passes() -> None:
    build = _build()
    effect_ranked = _effect_ranked(
        build,
        (("upstream-failure", RotationCandidateTier.INELIGIBLE),),
    )

    ranked = RotationCandidateTemporalEffectService().evaluate_and_rank(
        build=build,
        candidates=(
            RotationCandidateTemporalEffectInput(
                effect_ranked[0],
                applications=(_application(0.0), _application(20.0)),
            ),
        ),
        requirements=(_requirement(),),
    )

    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert ranked[0].failed_temporal_assessments == ()


def test_unresolved_temporal_effect_evidence_fails_closed() -> None:
    build = _build(include_proc=False)
    effect_ranked = _effect_ranked(
        build,
        (("unknown-proc", RotationCandidateTier.ELIGIBLE),),
    )

    ranked = RotationCandidateTemporalEffectService().evaluate_and_rank(
        build=build,
        candidates=(
            RotationCandidateTemporalEffectInput(
                effect_ranked[0],
                applications=(_application(0.0),),
            ),
        ),
        requirements=(_requirement(),),
    )

    assessment = ranked[0].temporal_assessments[0]
    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert assessment.observed_uptime is None
    assert any("no exact proc effect" in text for text in assessment.unresolved)
    assert any("evidence missing" in reason for reason in ranked[0].reasons)


def test_no_temporal_requirements_preserves_upstream_order() -> None:
    build = _build()
    effect_ranked = _effect_ranked(
        build,
        (
            ("second", RotationCandidateTier.ELIGIBLE),
            ("first", RotationCandidateTier.ELIGIBLE),
        ),
    )

    ranked = RotationCandidateTemporalEffectService().evaluate_and_rank(
        build=build,
        candidates=tuple(RotationCandidateTemporalEffectInput(item) for item in effect_ranked),
    )

    assert [item.candidate_id for item in ranked] == ["second", "first"]
    assert all(item.temporal_assessments == () for item in ranked)


def test_duplicate_temporal_candidate_ids_fail_closed() -> None:
    build = _build()
    effect_ranked = _effect_ranked(
        build,
        (("same", RotationCandidateTier.ELIGIBLE),),
    )
    candidate = RotationCandidateTemporalEffectInput(effect_ranked[0])

    with pytest.raises(ValueError, match="duplicate rotation temporal candidate_id"):
        RotationCandidateTemporalEffectService().evaluate_and_rank(
            build=build,
            candidates=(candidate, candidate),
        )
