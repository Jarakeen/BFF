from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingResult,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_effect_uptime_service import RotationEffectUptimeAssessment


@dataclass(frozen=True)
class RotationEffectObligationCandidate:
    """One already-scored rotation candidate plus build-specific effect evidence."""

    ranking_input: RotationCandidateRankingInput
    effect_uptime_assessments: tuple[RotationEffectUptimeAssessment, ...] = ()


@dataclass(frozen=True)
class RotationEffectObligationRankingResult:
    """Final candidate ordering after effect uptime is treated as a hard gate."""

    candidate_id: str
    base_result: RotationCandidateRankingResult
    effect_uptime_assessments: tuple[RotationEffectUptimeAssessment, ...]
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]

    @property
    def failed_effect_uptime_assessments(self) -> tuple[RotationEffectUptimeAssessment, ...]:
        return tuple(
            assessment
            for assessment in self.effect_uptime_assessments
            if not assessment.satisfied
        )


class _BaseRanker(Protocol):
    def rank(
        self,
        candidates: tuple[RotationCandidateRankingInput, ...],
    ) -> tuple[RotationCandidateRankingResult, ...]: ...


class RotationCandidateEffectObligationService:
    """Apply build-specific effect uptime as a hard candidate obligation.

    The generic candidate scorecard intentionally remains build-agnostic. This
    thin composition layer joins that scorecard ranking with build-specific
    effect-uptime assessments. Candidates that miss required effect coverage,
    or lack evidence needed to prove it, are ineligible even when their resource
    consequences or other soft metrics are better.

    Existing hard obligations remain authoritative through the delegated base
    ranking service; this layer never invents an effect target or uptime floor.
    """

    def __init__(self, base_ranker: _BaseRanker | None = None) -> None:
        self.base_ranker = base_ranker or RotationCandidateRankingService()

    def rank(
        self,
        candidates: tuple[RotationEffectObligationCandidate, ...],
    ) -> tuple[RotationEffectObligationRankingResult, ...]:
        if not candidates:
            return ()

        by_id: dict[str, RotationEffectObligationCandidate] = {}
        for candidate in candidates:
            candidate_id = candidate.ranking_input.candidate_id
            key = candidate_id.casefold()
            if key in by_id:
                raise ValueError(
                    f"duplicate rotation effect-obligation candidate_id: {candidate_id!r}"
                )
            by_id[key] = candidate
            self._validate_assessments(candidate)

        base_results = self.base_ranker.rank(
            tuple(candidate.ranking_input for candidate in candidates)
        )
        if {result.candidate_id.casefold() for result in base_results} != set(by_id):
            raise ValueError("base rotation ranking did not return the same candidate set")

        staged: list[tuple[tuple[object, ...], RotationEffectObligationRankingResult]] = []
        for base_result in base_results:
            candidate = by_id[base_result.candidate_id.casefold()]
            failed = tuple(
                assessment
                for assessment in candidate.effect_uptime_assessments
                if not assessment.satisfied
            )
            combined_eligible = (
                base_result.tier is RotationCandidateTier.ELIGIBLE and not failed
            )
            evidence_missing = sum(
                1 for assessment in failed if assessment.observed_uptime is None
            )
            shortfall = sum(
                assessment.shortfall or 0.0
                for assessment in failed
                if assessment.observed_uptime is not None
            )
            reasons = tuple(base_result.reasons) + self._effect_reasons(failed)
            result = RotationEffectObligationRankingResult(
                candidate_id=base_result.candidate_id,
                base_result=base_result,
                effect_uptime_assessments=candidate.effect_uptime_assessments,
                tier=(
                    RotationCandidateTier.ELIGIBLE
                    if combined_eligible
                    else RotationCandidateTier.INELIGIBLE
                ),
                rank=0,
                reasons=reasons,
            )
            staged.append(
                (
                    (
                        0 if combined_eligible else 1,
                        len(failed),
                        evidence_missing,
                        shortfall,
                        0 if base_result.tier is RotationCandidateTier.ELIGIBLE else 1,
                        base_result.rank,
                        base_result.candidate_id.casefold(),
                    ),
                    result,
                )
            )

        staged.sort(key=lambda item: item[0])
        return tuple(
            RotationEffectObligationRankingResult(
                candidate_id=result.candidate_id,
                base_result=result.base_result,
                effect_uptime_assessments=result.effect_uptime_assessments,
                tier=result.tier,
                rank=index + 1,
                reasons=result.reasons,
            )
            for index, (_key, result) in enumerate(staged)
        )

    @staticmethod
    def _validate_assessments(candidate: RotationEffectObligationCandidate) -> None:
        seen: set[tuple[str, str, str | None]] = set()
        for assessment in candidate.effect_uptime_assessments:
            requirement = assessment.requirement
            key = (
                requirement.effect_name.casefold(),
                requirement.source_skill_name.casefold(),
                requirement.bar,
            )
            if key in seen:
                raise ValueError(
                    "duplicate effect uptime assessment for candidate "
                    f"{candidate.ranking_input.candidate_id!r}: "
                    f"{requirement.effect_name!r} from {requirement.source_skill_name!r}"
                )
            seen.add(key)

    @staticmethod
    def _effect_reasons(
        failed: tuple[RotationEffectUptimeAssessment, ...],
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        for assessment in failed:
            requirement = assessment.requirement
            scope = f" on {requirement.bar} bar" if requirement.bar else ""
            source = f" from {requirement.source_skill_name!r}{scope}"
            if assessment.observed_uptime is None:
                details = "; ".join(assessment.unresolved) or "evidence unavailable"
                reasons.append(
                    f"effect uptime evidence missing for {requirement.effect_name!r}"
                    f"{source}: {details}"
                )
            else:
                reasons.append(
                    f"effect uptime below minimum for {requirement.effect_name!r}"
                    f"{source}: observed {assessment.observed_uptime:.2%}, "
                    f"required {requirement.minimum_uptime:.2%}"
                )
        return tuple(reasons)


__all__ = [
    "RotationCandidateEffectObligationService",
    "RotationEffectObligationCandidate",
    "RotationEffectObligationRankingResult",
]
