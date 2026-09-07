from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from services.rotation_candidate_effect_obligation_service import (
    RotationCandidateEffectObligationService,
    RotationEffectObligationCandidate,
    RotationEffectObligationRankingResult,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_ranking_service import RotationCandidateRankingInput
from services.rotation_effect_uptime_service import (
    RotationEffectUptimeRequirement,
    RotationEffectUptimeService,
)


@dataclass(frozen=True)
class RotationCandidateEffectEvaluationInput:
    """Join one generated schedule candidate to its generic scorecard evidence."""

    generated_candidate: GeneratedRotationCandidate
    ranking_input: RotationCandidateRankingInput

    def __post_init__(self) -> None:
        generated_id = self.generated_candidate.candidate_id.strip().casefold()
        ranking_id = self.ranking_input.candidate_id.strip().casefold()
        if generated_id != ranking_id:
            raise ValueError(
                "generated rotation candidate and ranking input must use the same candidate_id"
            )


@dataclass(frozen=True)
class RotationCandidateEffectEvaluationResult:
    """Final ranked candidate with its generated schedule retained for downstream use."""

    generated_candidate: GeneratedRotationCandidate
    ranking_result: RotationEffectObligationRankingResult

    @property
    def candidate_id(self) -> str:
        return self.ranking_result.candidate_id

    @property
    def rank(self) -> int:
        return self.ranking_result.rank

    @property
    def tier(self):
        return self.ranking_result.tier


class _EffectUptimeAssessor(Protocol):
    def assess(
        self,
        *,
        plan,
        build: CharacterBuild,
        requirements: tuple[RotationEffectUptimeRequirement, ...],
        passives: Iterable[PassiveGrant] = (),
    ): ...


class _EffectObligationRanker(Protocol):
    def rank(
        self,
        candidates: tuple[RotationEffectObligationCandidate, ...],
    ) -> tuple[RotationEffectObligationRankingResult, ...]: ...


class RotationCandidateEffectEvaluationService:
    """Evaluate build-specific effect obligations for every generated candidate.

    Candidate generation, generic scorecards, and build-specific effect timing stay
    deliberately separate. This service is the composition boundary that removes a
    manual caller step: every generated plan is assessed against the same explicit
    effect-uptime requirements before final eligibility/ranking is returned.

    Unknown or unresolved effect timing remains a hard failure through the existing
    effect-obligation gate. This layer does not invent requirements, uptime floors,
    effect identities, or build mechanics.
    """

    def __init__(
        self,
        uptime_service: _EffectUptimeAssessor | None = None,
        obligation_service: _EffectObligationRanker | None = None,
    ) -> None:
        self.uptime_service = uptime_service or RotationEffectUptimeService()
        self.obligation_service = (
            obligation_service or RotationCandidateEffectObligationService()
        )

    def evaluate_and_rank(
        self,
        *,
        build: CharacterBuild,
        candidates: tuple[RotationCandidateEffectEvaluationInput, ...],
        requirements: tuple[RotationEffectUptimeRequirement, ...] = (),
        passives: Iterable[PassiveGrant] = (),
    ) -> tuple[RotationCandidateEffectEvaluationResult, ...]:
        if not candidates:
            return ()

        by_id: dict[str, GeneratedRotationCandidate] = {}
        obligation_candidates: list[RotationEffectObligationCandidate] = []
        passive_tuple = tuple(passives)

        for candidate in candidates:
            candidate_id = candidate.generated_candidate.candidate_id
            key = candidate_id.casefold()
            if key in by_id:
                raise ValueError(
                    f"duplicate rotation effect-evaluation candidate_id: {candidate_id!r}"
                )
            by_id[key] = candidate.generated_candidate

            assessments = self.uptime_service.assess(
                plan=candidate.generated_candidate.plan,
                build=build,
                requirements=tuple(requirements),
                passives=passive_tuple,
            )
            obligation_candidates.append(
                RotationEffectObligationCandidate(
                    ranking_input=candidate.ranking_input,
                    effect_uptime_assessments=tuple(assessments),
                )
            )

        ranked = self.obligation_service.rank(tuple(obligation_candidates))
        if {item.candidate_id.casefold() for item in ranked} != set(by_id):
            raise ValueError(
                "effect-obligation ranking did not return the same candidate set"
            )

        return tuple(
            RotationCandidateEffectEvaluationResult(
                generated_candidate=by_id[item.candidate_id.casefold()],
                ranking_result=item,
            )
            for item in ranked
        )


__all__ = [
    "RotationCandidateEffectEvaluationInput",
    "RotationCandidateEffectEvaluationResult",
    "RotationCandidateEffectEvaluationService",
]
