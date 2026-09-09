from __future__ import annotations

from dataclasses import dataclass
import re
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

    Among candidates that satisfy every explicit uptime floor, effect coverage is
    then treated as a Pareto preference rather than collapsed into a weighted
    score. A candidate is uptime-dominated only when another eligible candidate is
    at least as good on every required effect and strictly better on at least one.
    Incomparable uptime tradeoffs remain on the same frontier and retain the base
    ranker's ordering. This keeps arithmetic evidence separate from encounter/role
    policy while still preferring plainly better support coverage.

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
        self._validate_common_requirement_set(tuple(by_id.values()))

        base_results = self.base_ranker.rank(
            tuple(candidate.ranking_input for candidate in candidates)
        )
        if {result.candidate_id.casefold() for result in base_results} != set(by_id):
            raise ValueError("base rotation ranking did not return the same candidate set")

        intermediate: dict[str, RotationEffectObligationRankingResult] = {}
        combined_eligible: set[str] = set()
        failed_by_id: dict[str, tuple[RotationEffectUptimeAssessment, ...]] = {}

        for base_result in base_results:
            key = base_result.candidate_id.casefold()
            candidate = by_id[key]
            failed = tuple(
                assessment
                for assessment in candidate.effect_uptime_assessments
                if not assessment.satisfied
            )
            failed_by_id[key] = failed
            is_eligible = (
                base_result.tier is RotationCandidateTier.ELIGIBLE and not failed
            )
            if is_eligible:
                combined_eligible.add(key)
            intermediate[key] = RotationEffectObligationRankingResult(
                candidate_id=base_result.candidate_id,
                base_result=base_result,
                effect_uptime_assessments=candidate.effect_uptime_assessments,
                tier=(
                    RotationCandidateTier.ELIGIBLE
                    if is_eligible
                    else RotationCandidateTier.INELIGIBLE
                ),
                rank=0,
                reasons=tuple(base_result.reasons) + self._effect_reasons(failed),
            )

        dominators_by_id: dict[str, tuple[str, ...]] = {}
        for candidate_key in combined_eligible:
            dominators = tuple(
                intermediate[other_key].candidate_id
                for other_key in combined_eligible
                if other_key != candidate_key
                and self._uptime_dominates(
                    by_id[other_key],
                    by_id[candidate_key],
                )
            )
            dominators_by_id[candidate_key] = tuple(
                sorted(dominators, key=str.casefold)
            )

        staged: list[tuple[tuple[object, ...], RotationEffectObligationRankingResult]] = []
        for base_result in base_results:
            key = base_result.candidate_id.casefold()
            result = intermediate[key]
            failed = failed_by_id[key]
            is_eligible = key in combined_eligible
            dominators = dominators_by_id.get(key, ())

            evidence_missing = sum(
                1 for assessment in failed if assessment.observed_uptime is None
            )
            shortfall = sum(
                assessment.shortfall or 0.0
                for assessment in failed
                if assessment.observed_uptime is not None
            )
            reasons = result.reasons
            if is_eligible and dominators:
                reasons += (
                    "effect uptime Pareto-dominated by " + ", ".join(dominators),
                )
                result = RotationEffectObligationRankingResult(
                    candidate_id=result.candidate_id,
                    base_result=result.base_result,
                    effect_uptime_assessments=result.effect_uptime_assessments,
                    tier=result.tier,
                    rank=0,
                    reasons=reasons,
                )

            staged.append(
                (
                    (
                        0 if is_eligible and not dominators else 1 if is_eligible else 2,
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

    @classmethod
    def _validate_assessments(cls, candidate: RotationEffectObligationCandidate) -> None:
        seen: set[tuple[str, str, str | None]] = set()
        for assessment in candidate.effect_uptime_assessments:
            requirement = assessment.requirement
            key = cls._requirement_key(assessment)
            if key in seen:
                raise ValueError(
                    "duplicate effect uptime assessment for candidate "
                    f"{candidate.ranking_input.candidate_id!r}: "
                    f"{requirement.effect_name!r} from {requirement.source_skill_name!r}"
                )
            seen.add(key)

    @classmethod
    def _validate_common_requirement_set(
        cls,
        candidates: tuple[RotationEffectObligationCandidate, ...],
    ) -> None:
        expected: set[tuple[str, str, str | None]] | None = None
        for candidate in candidates:
            current = {
                cls._requirement_key(assessment)
                for assessment in candidate.effect_uptime_assessments
            }
            if expected is None:
                expected = current
                continue
            if current != expected:
                raise ValueError(
                    "effect uptime candidates must carry the same explicit requirement set"
                )

    @classmethod
    def _uptime_dominates(
        cls,
        left: RotationEffectObligationCandidate,
        right: RotationEffectObligationCandidate,
    ) -> bool:
        left_map = {
            cls._requirement_key(assessment): assessment.observed_uptime
            for assessment in left.effect_uptime_assessments
        }
        right_map = {
            cls._requirement_key(assessment): assessment.observed_uptime
            for assessment in right.effect_uptime_assessments
        }
        if not left_map or left_map.keys() != right_map.keys():
            return False
        if any(value is None for value in left_map.values()) or any(
            value is None for value in right_map.values()
        ):
            return False

        at_least_as_good = all(
            float(left_map[key]) >= float(right_map[key])
            for key in left_map
        )
        strictly_better = any(
            float(left_map[key]) > float(right_map[key])
            for key in left_map
        )
        return at_least_as_good and strictly_better

    @classmethod
    def _requirement_key(
        cls,
        assessment: RotationEffectUptimeAssessment,
    ) -> tuple[str, str, str | None]:
        requirement = assessment.requirement
        return (
            requirement.effect_name.casefold(),
            cls._stable_skill_id(requirement.source_skill_name),
            requirement.bar,
        )

    @staticmethod
    def _stable_skill_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

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
