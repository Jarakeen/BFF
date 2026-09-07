from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_candidate_temporal_effect_service import (
    RotationCandidateTemporalEffectResult,
)
from services.rotation_plan_temporal_legality_service import (
    RotationPlanTemporalLegalityAssessment,
    RotationPlanTemporalLegalityService,
)
from services.rotation_temporal_effect_legality_service import (
    RotationTemporalEffectLegalityAssessment,
    RotationTemporalEffectLegalityService,
)
from services.rotation_temporal_effect_uptime_service import (
    RotationTemporalEffectApplication,
)


@dataclass(frozen=True)
class RotationCandidateTemporalLegalityInput:
    temporal_result: RotationCandidateTemporalEffectResult
    applications: tuple[RotationTemporalEffectApplication, ...]
    initial_bar: str


@dataclass(frozen=True)
class RotationCandidateTemporalLegalityResult:
    temporal_result: RotationCandidateTemporalEffectResult
    effect_legality: RotationTemporalEffectLegalityAssessment
    plan_legality: RotationPlanTemporalLegalityAssessment
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]

    @property
    def candidate_id(self) -> str:
        return self.temporal_result.candidate_id

    @property
    def generated_candidate(self):
        return self.temporal_result.generated_candidate


class RotationCandidateTemporalLegalityService:
    """Apply build and plan temporal legality as a final hard candidate gate."""

    def __init__(
        self,
        *,
        effect_legality_service: RotationTemporalEffectLegalityService | None = None,
        plan_legality_service: RotationPlanTemporalLegalityService | None = None,
    ) -> None:
        self.effect_legality_service = (
            effect_legality_service or RotationTemporalEffectLegalityService()
        )
        self.plan_legality_service = (
            plan_legality_service or RotationPlanTemporalLegalityService()
        )

    def evaluate_and_rank(
        self,
        *,
        build: CharacterBuild,
        candidates: tuple[RotationCandidateTemporalLegalityInput, ...],
        passives: Iterable[PassiveGrant] = (),
    ) -> tuple[RotationCandidateTemporalLegalityResult, ...]:
        if not candidates:
            return ()

        passive_tuple = tuple(passives)
        seen: set[str] = set()
        staged: list[
            tuple[tuple[object, ...], RotationCandidateTemporalLegalityResult]
        ] = []

        for candidate in candidates:
            candidate_id = candidate.temporal_result.candidate_id
            key = candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate rotation temporal-legality candidate_id: {candidate_id!r}"
                )
            seen.add(key)

            effect_legality = self.effect_legality_service.assess(
                build=build,
                applications=tuple(candidate.applications),
                passives=passive_tuple,
            )
            plan_legality = self.plan_legality_service.assess(
                plan=candidate.temporal_result.generated_candidate.plan,
                applications=tuple(candidate.applications),
                initial_bar=candidate.initial_bar,
            )

            upstream_eligible = (
                candidate.temporal_result.tier is RotationCandidateTier.ELIGIBLE
            )
            legal = effect_legality.is_legal and plan_legality.is_legal
            combined_eligible = upstream_eligible and legal
            unresolved_count = len(effect_legality.unresolved) + len(plan_legality.unresolved)
            violation_count = len(effect_legality.violations) + len(plan_legality.violations)
            reasons = (
                tuple(candidate.temporal_result.reasons)
                + self._effect_legality_reasons(effect_legality)
                + self._plan_legality_reasons(plan_legality)
            )
            result = RotationCandidateTemporalLegalityResult(
                temporal_result=candidate.temporal_result,
                effect_legality=effect_legality,
                plan_legality=plan_legality,
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
                        unresolved_count,
                        violation_count,
                        0 if upstream_eligible else 1,
                        candidate.temporal_result.rank,
                        candidate_id.casefold(),
                    ),
                    result,
                )
            )

        staged.sort(key=lambda item: item[0])
        return tuple(
            RotationCandidateTemporalLegalityResult(
                temporal_result=result.temporal_result,
                effect_legality=result.effect_legality,
                plan_legality=result.plan_legality,
                tier=result.tier,
                rank=index + 1,
                reasons=result.reasons,
            )
            for index, (_key, result) in enumerate(staged)
        )

    @staticmethod
    def _effect_legality_reasons(
        assessment: RotationTemporalEffectLegalityAssessment,
    ) -> tuple[str, ...]:
        reasons = [
            f"temporal effect legality violation for {item.effect_name!r} from "
            f"{item.source!r} at {item.time_seconds:.3f}s: {item.reason}"
            for item in assessment.violations
        ]
        reasons.extend(
            f"temporal effect legality unresolved: {item}"
            for item in assessment.unresolved
        )
        return tuple(reasons)

    @staticmethod
    def _plan_legality_reasons(
        assessment: RotationPlanTemporalLegalityAssessment,
    ) -> tuple[str, ...]:
        reasons = [
            f"rotation plan temporal legality violation for {item.effect_name!r} from "
            f"{item.source!r} at {item.time_seconds:.3f}s: {item.reason}"
            for item in assessment.violations
        ]
        reasons.extend(
            f"rotation plan temporal legality unresolved: {item}"
            for item in assessment.unresolved
        )
        return tuple(reasons)


__all__ = [
    "RotationCandidateTemporalLegalityInput",
    "RotationCandidateTemporalLegalityResult",
    "RotationCandidateTemporalLegalityService",
]
