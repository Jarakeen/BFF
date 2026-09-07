from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from services.rotation_candidate_effect_evaluation_service import (
    RotationCandidateEffectEvaluationResult,
)
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_temporal_effect_uptime_service import (
    RotationTemporalEffectApplication,
    RotationTemporalEffectAssessment,
    RotationTemporalEffectRequirement,
    RotationTemporalEffectUptimeService,
)


@dataclass(frozen=True)
class RotationCandidateTemporalEffectInput:
    """One cast-effect-ranked candidate plus explicit temporal activations."""

    effect_result: RotationCandidateEffectEvaluationResult
    applications: tuple[RotationTemporalEffectApplication, ...] = ()


@dataclass(frozen=True)
class RotationCandidateTemporalEffectResult:
    """Final candidate state after proc/ultimate/consumable hard obligations."""

    effect_result: RotationCandidateEffectEvaluationResult
    temporal_assessments: tuple[RotationTemporalEffectAssessment, ...]
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]

    @property
    def candidate_id(self) -> str:
        return self.effect_result.candidate_id

    @property
    def generated_candidate(self):
        return self.effect_result.generated_candidate

    @property
    def failed_temporal_assessments(self) -> tuple[RotationTemporalEffectAssessment, ...]:
        return tuple(item for item in self.temporal_assessments if not item.satisfied)


class RotationCandidateTemporalEffectService:
    """Apply explicit non-cast temporal effect coverage as a final hard gate.

    Cast-produced effect obligations remain authoritative in the upstream
    RotationCandidateEffectEvaluationResult. This layer adds only explicit
    PROC/ULTIMATE/CONSUMABLE timing evidence. It never invents activations from
    cooldowns, proc chance, or mere build availability.
    """

    def __init__(self, uptime_service: RotationTemporalEffectUptimeService | None = None) -> None:
        self.uptime_service = uptime_service or RotationTemporalEffectUptimeService()

    def evaluate_and_rank(
        self,
        *,
        build: CharacterBuild,
        candidates: tuple[RotationCandidateTemporalEffectInput, ...],
        requirements: tuple[RotationTemporalEffectRequirement, ...] = (),
        passives: Iterable[PassiveGrant] = (),
    ) -> tuple[RotationCandidateTemporalEffectResult, ...]:
        if not candidates:
            return ()

        seen: set[str] = set()
        staged: list[tuple[tuple[object, ...], RotationCandidateTemporalEffectResult]] = []
        passive_tuple = tuple(passives)

        for candidate in candidates:
            candidate_id = candidate.effect_result.candidate_id
            key = candidate_id.casefold()
            if key in seen:
                raise ValueError(f"duplicate rotation temporal candidate_id: {candidate_id!r}")
            seen.add(key)

            plan = candidate.effect_result.generated_candidate.plan
            assessments = self.uptime_service.assess(
                duration_seconds=plan.duration_seconds,
                build=build,
                requirements=tuple(requirements),
                applications=tuple(candidate.applications),
                passives=passive_tuple,
            )
            failed = tuple(item for item in assessments if not item.satisfied)
            upstream_eligible = candidate.effect_result.tier is RotationCandidateTier.ELIGIBLE
            combined_eligible = upstream_eligible and not failed
            evidence_missing = sum(1 for item in failed if item.observed_uptime is None)
            shortfall = sum(
                item.shortfall or 0.0
                for item in failed
                if item.observed_uptime is not None
            )
            reasons = tuple(candidate.effect_result.ranking_result.reasons) + self._temporal_reasons(failed)
            result = RotationCandidateTemporalEffectResult(
                effect_result=candidate.effect_result,
                temporal_assessments=tuple(assessments),
                tier=(RotationCandidateTier.ELIGIBLE if combined_eligible else RotationCandidateTier.INELIGIBLE),
                rank=0,
                reasons=reasons,
            )
            staged.append((
                (
                    0 if combined_eligible else 1,
                    len(failed),
                    evidence_missing,
                    shortfall,
                    0 if upstream_eligible else 1,
                    candidate.effect_result.rank,
                    candidate_id.casefold(),
                ),
                result,
            ))

        staged.sort(key=lambda item: item[0])
        return tuple(
            RotationCandidateTemporalEffectResult(
                effect_result=result.effect_result,
                temporal_assessments=result.temporal_assessments,
                tier=result.tier,
                rank=index + 1,
                reasons=result.reasons,
            )
            for index, (_sort_key, result) in enumerate(staged)
        )

    @staticmethod
    def _temporal_reasons(
        failed: tuple[RotationTemporalEffectAssessment, ...],
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        for assessment in failed:
            requirement = assessment.requirement
            source = f" from {requirement.source!r} ({requirement.layer.value})"
            if assessment.observed_uptime is None:
                details = "; ".join(assessment.unresolved) or "evidence unavailable"
                reasons.append(
                    f"temporal effect uptime evidence missing for {requirement.effect_name!r}"
                    f"{source}: {details}"
                )
            else:
                reasons.append(
                    f"temporal effect uptime below minimum for {requirement.effect_name!r}"
                    f"{source}: observed {assessment.observed_uptime:.2%}, "
                    f"required {requirement.minimum_uptime:.2%}"
                )
        return tuple(reasons)


__all__ = [
    "RotationCandidateTemporalEffectInput",
    "RotationCandidateTemporalEffectResult",
    "RotationCandidateTemporalEffectService",
]
