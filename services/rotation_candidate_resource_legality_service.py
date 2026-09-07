from __future__ import annotations

from dataclasses import dataclass

from minmax.potion_cadence import BASE_POTION_COOLDOWN_SECONDS
from minmax.ultimate_resource_timeline import UltimateGenerationEvent, UltimateSpendRule
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_candidate_temporal_legality_service import (
    RotationCandidateTemporalLegalityResult,
)
from services.rotation_scheduled_action_resource_legality_service import (
    RotationScheduledActionResourceAssessment,
    RotationScheduledActionResourceLegalityService,
)


@dataclass(frozen=True)
class RotationCandidateResourceLegalityInput:
    """One temporally legal candidate plus explicit resource evidence."""

    legality_result: RotationCandidateTemporalLegalityResult
    starting_ultimate: float = 0.0
    ultimate_generation_events: tuple[UltimateGenerationEvent, ...] = ()
    ultimate_spend_rules: tuple[UltimateSpendRule, ...] = ()
    potion_cooldown_seconds: float = BASE_POTION_COOLDOWN_SECONDS


@dataclass(frozen=True)
class RotationCandidateResourceLegalityResult:
    """Candidate state after scheduled Ultimate/potion resource legality."""

    legality_result: RotationCandidateTemporalLegalityResult
    resource_legality: RotationScheduledActionResourceAssessment
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]

    @property
    def candidate_id(self) -> str:
        return self.legality_result.candidate_id

    @property
    def generated_candidate(self):
        return self.legality_result.generated_candidate


class RotationCandidateResourceLegalityService:
    """Apply scheduled Ultimate and potion legality as another hard gate.

    All upstream candidate obligations remain authoritative. This layer only asks
    whether the already-generated schedule can pay for its explicit Ultimate casts
    from supplied resource evidence and whether scheduled potion uses respect the
    supplied canonical/effective cooldown.

    Unknown Ultimate costs and same-timestamp affordability ambiguity remain
    unresolved and therefore make a candidate ineligible. This service does not
    infer generation, costs, potion reductions, or encounter-specific resource
    events.
    """

    def __init__(
        self,
        resource_service: RotationScheduledActionResourceLegalityService | None = None,
    ) -> None:
        self.resource_service = (
            resource_service or RotationScheduledActionResourceLegalityService()
        )

    def evaluate_and_rank(
        self,
        *,
        candidates: tuple[RotationCandidateResourceLegalityInput, ...],
    ) -> tuple[RotationCandidateResourceLegalityResult, ...]:
        if not candidates:
            return ()

        seen: set[str] = set()
        staged: list[
            tuple[tuple[object, ...], RotationCandidateResourceLegalityResult]
        ] = []

        for candidate in candidates:
            candidate_id = candidate.legality_result.candidate_id
            key = candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate rotation resource-legality candidate_id: {candidate_id!r}"
                )
            seen.add(key)

            plan = candidate.legality_result.generated_candidate.plan
            assessment = self.resource_service.assess(
                plan=plan,
                starting_ultimate=candidate.starting_ultimate,
                ultimate_generation_events=tuple(candidate.ultimate_generation_events),
                ultimate_spend_rules=tuple(candidate.ultimate_spend_rules),
                potion_cooldown_seconds=candidate.potion_cooldown_seconds,
            )

            upstream_eligible = (
                candidate.legality_result.tier is RotationCandidateTier.ELIGIBLE
            )
            combined_eligible = upstream_eligible and assessment.is_legal
            reasons = (
                tuple(candidate.legality_result.reasons)
                + self._resource_legality_reasons(assessment)
            )
            result = RotationCandidateResourceLegalityResult(
                legality_result=candidate.legality_result,
                resource_legality=assessment,
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
                        len(assessment.unresolved),
                        len(assessment.violations),
                        0 if upstream_eligible else 1,
                        candidate.legality_result.rank,
                        candidate_id.casefold(),
                    ),
                    result,
                )
            )

        staged.sort(key=lambda item: item[0])
        return tuple(
            RotationCandidateResourceLegalityResult(
                legality_result=result.legality_result,
                resource_legality=result.resource_legality,
                tier=result.tier,
                rank=index + 1,
                reasons=result.reasons,
            )
            for index, (_key, result) in enumerate(staged)
        )

    @staticmethod
    def _resource_legality_reasons(
        assessment: RotationScheduledActionResourceAssessment,
    ) -> tuple[str, ...]:
        reasons = [
            f"scheduled {item.action_kind.value} resource legality violation for "
            f"{item.action_name!r} at {item.time_seconds:.3f}s: {item.reason}"
            for item in assessment.violations
        ]
        reasons.extend(
            f"scheduled action resource legality unresolved: {item}"
            for item in assessment.unresolved
        )
        return tuple(reasons)


__all__ = [
    "RotationCandidateResourceLegalityInput",
    "RotationCandidateResourceLegalityResult",
    "RotationCandidateResourceLegalityService",
]
