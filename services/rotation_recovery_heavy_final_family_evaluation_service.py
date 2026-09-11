from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Callable, Protocol

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from services.rotation_candidate_effect_obligation_service import (
    RotationCandidateEffectObligationService,
    RotationEffectObligationCandidate,
    RotationEffectObligationRankingResult,
)
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingResult,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_effect_uptime_service import (
    RotationEffectUptimeRequirement,
    RotationEffectUptimeService,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryFinalFamilyEvaluator,
    RecoveryHeavyStabilizedCandidateSnapshot,
)
from services.rotation_role_aware_ranking_service import (
    RotationRoleAwareRankingInput,
    RotationRoleAwareRankingResult,
    RotationRoleAwareRankingService,
)
from services.rotation_target_capacity_ranking_service import (
    RotationTargetCapacityRankingService,
)


RecoveryFinalScorecardResolver = Callable[
    [RecoveryHeavyStabilizedCandidateSnapshot],
    RotationCandidateScorecard,
]
RecoveryFinalRoleAwareInputResolver = Callable[
    [RecoveryHeavyStabilizedCandidateSnapshot],
    RotationRoleAwareRankingInput,
]


@dataclass(frozen=True)
class RecoveryRoleAwareFinalCandidateEvaluation:
    """Selection-compatible wrapper around canonical role-aware ranking evidence."""

    candidate_id: str
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]
    role_ranking: RotationRoleAwareRankingResult


class _BaseRanker(Protocol):
    def rank(
        self,
        candidates: tuple[RotationCandidateRankingInput, ...],
    ) -> tuple[RotationCandidateRankingResult, ...]: ...


class _RoleAwareRanker(Protocol):
    def rank(
        self,
        candidates: tuple[RotationRoleAwareRankingInput, ...],
    ) -> tuple[RotationRoleAwareRankingResult, ...]: ...


class _EffectUptimeAssessor(Protocol):
    def assess(
        self,
        *,
        plan,
        build: CharacterBuild,
        requirements: tuple[RotationEffectUptimeRequirement, ...],
        passives: Iterable[PassiveGrant] = (),
    ): ...


class _EffectRanker(Protocol):
    def rank(
        self,
        candidates: tuple[RotationEffectObligationCandidate, ...],
    ) -> tuple[RotationEffectObligationRankingResult, ...]: ...


class RotationRecoveryHeavyFinalFamilyEvaluationService:
    """Evaluate the actual final stabilized candidate family for final selection.

    Recovery stabilization can materially change the execution plan. Final ranking
    therefore must be rebuilt from those stabilized plans rather than reusing stale
    pre-recovery scorecards or effect evidence. This adapter supplies that concrete
    family-level boundary while preserving the existing separation of concerns:

    - callers resolve generic scorecard evidence from each final snapshot;
    - the canonical generic ranker compares the whole final family together;
    - optional role-aware callers may supply canonical role-ranking inputs for those
      same final snapshots so gameplay-practice policy participates before selection;
    - optional build-specific effect obligations are reassessed from each final plan;
    - passives are forwarded unchanged to the canonical build-aware uptime service.

    The role-aware path delegates entirely to ``RotationRoleAwareRankingService``.
    This service does not copy gameplay-policy ordering rules or invent role output,
    support value, sustain margin, displacement, or policy evidence.

    The default base ranker also recognizes explicit target-capacity scorecard
    evidence as a hard obligation. The effect-obligation ranker delegates to that
    same base ranker so capacity legality cannot disappear merely because effect
    uptime evaluation is also enabled.

    The service never invents encounter requirements, reserve thresholds, uptime
    floors, effect identities, passives, set behavior, target caps, role evidence,
    or strategy semantics.
    """

    def __init__(
        self,
        *,
        base_ranker: _BaseRanker | None = None,
        role_aware_ranker: _RoleAwareRanker | None = None,
        effect_uptime_service: _EffectUptimeAssessor | None = None,
        effect_ranker: _EffectRanker | None = None,
    ) -> None:
        self.base_ranker = base_ranker or RotationTargetCapacityRankingService()
        self.role_aware_ranker = role_aware_ranker or RotationRoleAwareRankingService()
        self.effect_uptime_service = effect_uptime_service or RotationEffectUptimeService()
        self.effect_ranker = effect_ranker or RotationCandidateEffectObligationService(
            base_ranker=self.base_ranker,
        )

    def evaluate_generic(
        self,
        snapshots: tuple[RecoveryHeavyStabilizedCandidateSnapshot, ...],
        *,
        scorecard_resolver: RecoveryFinalScorecardResolver,
    ) -> tuple[RotationCandidateRankingResult, ...]:
        ranking_inputs = self._ranking_inputs(
            snapshots=snapshots,
            scorecard_resolver=scorecard_resolver,
        )
        ranked = tuple(self.base_ranker.rank(ranking_inputs))
        self._validate_candidate_set(snapshots=snapshots, ranked=ranked)
        return ranked

    def evaluate_role_aware(
        self,
        snapshots: tuple[RecoveryHeavyStabilizedCandidateSnapshot, ...],
        *,
        input_resolver: RecoveryFinalRoleAwareInputResolver,
    ) -> tuple[RecoveryRoleAwareFinalCandidateEvaluation, ...]:
        inputs: list[RotationRoleAwareRankingInput] = []
        for snapshot in snapshots:
            resolved = input_resolver(snapshot)
            expected = str(snapshot.candidate_id or "").strip()
            actual = str(resolved.candidate_id or "").strip()
            if actual.casefold() != expected.casefold():
                raise ValueError(
                    "final recovery role-aware input candidate mismatch: "
                    f"expected {expected!r}, got {actual!r}"
                )
            inputs.append(resolved)

        ranked = tuple(self.role_aware_ranker.rank(tuple(inputs)))
        wrapped = tuple(
            RecoveryRoleAwareFinalCandidateEvaluation(
                candidate_id=item.candidate_id,
                tier=item.tier,
                rank=item.rank,
                reasons=item.base_ranking.reasons + item.role_reasons,
                role_ranking=item,
            )
            for item in ranked
        )
        self._validate_candidate_set(snapshots=snapshots, ranked=wrapped)
        return wrapped

    def evaluate_effects(
        self,
        snapshots: tuple[RecoveryHeavyStabilizedCandidateSnapshot, ...],
        *,
        build: CharacterBuild,
        scorecard_resolver: RecoveryFinalScorecardResolver,
        requirements: tuple[RotationEffectUptimeRequirement, ...] = (),
        passives: Iterable[PassiveGrant] = (),
    ) -> tuple[RotationEffectObligationRankingResult, ...]:
        ranking_inputs = self._ranking_inputs(
            snapshots=snapshots,
            scorecard_resolver=scorecard_resolver,
        )
        ranking_by_id = {
            item.candidate_id.casefold(): item
            for item in ranking_inputs
        }
        passive_tuple = tuple(passives)
        effect_candidates: list[RotationEffectObligationCandidate] = []

        for snapshot in snapshots:
            assessments = self.effect_uptime_service.assess(
                plan=snapshot.plan,
                build=build,
                requirements=tuple(requirements),
                passives=passive_tuple,
            )
            effect_candidates.append(
                RotationEffectObligationCandidate(
                    ranking_input=ranking_by_id[snapshot.candidate_id.casefold()],
                    effect_uptime_assessments=tuple(assessments),
                )
            )

        ranked = tuple(self.effect_ranker.rank(tuple(effect_candidates)))
        self._validate_candidate_set(snapshots=snapshots, ranked=ranked)
        return ranked

    def generic_evaluator(
        self,
        *,
        scorecard_resolver: RecoveryFinalScorecardResolver,
    ) -> RecoveryFinalFamilyEvaluator:
        def evaluate(
            snapshots: tuple[RecoveryHeavyStabilizedCandidateSnapshot, ...],
        ):
            return self.evaluate_generic(
                snapshots,
                scorecard_resolver=scorecard_resolver,
            )

        return evaluate

    def role_aware_evaluator(
        self,
        *,
        input_resolver: RecoveryFinalRoleAwareInputResolver,
    ) -> RecoveryFinalFamilyEvaluator:
        def evaluate(
            snapshots: tuple[RecoveryHeavyStabilizedCandidateSnapshot, ...],
        ):
            return self.evaluate_role_aware(
                snapshots,
                input_resolver=input_resolver,
            )

        return evaluate

    def effect_evaluator(
        self,
        *,
        build: CharacterBuild,
        scorecard_resolver: RecoveryFinalScorecardResolver,
        requirements: tuple[RotationEffectUptimeRequirement, ...] = (),
        passives: Iterable[PassiveGrant] = (),
    ) -> RecoveryFinalFamilyEvaluator:
        passive_tuple = tuple(passives)
        requirement_tuple = tuple(requirements)

        def evaluate(
            snapshots: tuple[RecoveryHeavyStabilizedCandidateSnapshot, ...],
        ):
            return self.evaluate_effects(
                snapshots,
                build=build,
                scorecard_resolver=scorecard_resolver,
                requirements=requirement_tuple,
                passives=passive_tuple,
            )

        return evaluate

    @staticmethod
    def _ranking_inputs(
        *,
        snapshots: tuple[RecoveryHeavyStabilizedCandidateSnapshot, ...],
        scorecard_resolver: RecoveryFinalScorecardResolver,
    ) -> tuple[RotationCandidateRankingInput, ...]:
        seen: set[str] = set()
        ranking_inputs: list[RotationCandidateRankingInput] = []
        for snapshot in snapshots:
            candidate_id = str(snapshot.candidate_id or "").strip()
            if not candidate_id:
                raise ValueError("final recovery snapshot candidate_id is empty")
            key = candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate final recovery snapshot candidate_id: {candidate_id!r}"
                )
            seen.add(key)
            ranking_inputs.append(
                RotationCandidateRankingInput(
                    candidate_id=candidate_id,
                    scorecard=scorecard_resolver(snapshot),
                )
            )
        return tuple(ranking_inputs)

    @staticmethod
    def _validate_candidate_set(
        *,
        snapshots: tuple[RecoveryHeavyStabilizedCandidateSnapshot, ...],
        ranked,
    ) -> None:
        expected = {snapshot.candidate_id.casefold() for snapshot in snapshots}
        actual = {str(item.candidate_id).casefold() for item in ranked}
        if expected != actual or len(ranked) != len(snapshots):
            raise ValueError(
                "final stabilized family ranking did not return the same candidate set"
            )


__all__ = [
    "RecoveryFinalRoleAwareInputResolver",
    "RecoveryFinalScorecardResolver",
    "RecoveryRoleAwareFinalCandidateEvaluation",
    "RotationRecoveryHeavyFinalFamilyEvaluationService",
]
