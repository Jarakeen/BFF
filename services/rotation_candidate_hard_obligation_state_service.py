from __future__ import annotations

from services.rotation_candidate_effect_obligation_service import (
    RotationEffectObligationRankingResult,
)
from services.rotation_candidate_ranking_service import RotationCandidateRankingResult
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard


class RotationCandidateHardObligationStateService:
    """Project canonical candidate hard failures into deterministic fixed-point state.

    The projection deliberately excludes rank, resource consequence preferences,
    runtime-uptime objectives, scheduler notes, and other soft comparison evidence.
    Recovery-heavy stabilization only needs to know whether the regenerated plan
    still satisfies the same explicit obligations. It must not oscillate merely
    because a soft preference score changed.
    """

    def from_ranking_result(
        self,
        result: RotationCandidateRankingResult,
    ) -> tuple[str, ...]:
        return self.from_scorecard(result.scorecard)

    def from_effect_ranking_result(
        self,
        result: RotationEffectObligationRankingResult,
    ) -> tuple[str, ...]:
        state = list(self.from_scorecard(result.base_result.scorecard))
        for assessment in result.failed_effect_uptime_assessments:
            requirement = assessment.requirement
            state.append(
                self._token(
                    "effect_uptime",
                    requirement.effect_name,
                    requirement.source_skill_name,
                    requirement.bar or "any",
                    self._number(requirement.minimum_uptime),
                    self._optional_number(assessment.observed_uptime),
                    *tuple(assessment.unresolved),
                )
            )
        return tuple(sorted(state, key=str.casefold))

    def from_scorecard(
        self,
        scorecard: RotationCandidateScorecard,
    ) -> tuple[str, ...]:
        state: list[str] = []

        for requirement in scorecard.missing_demand_requirements:
            state.append(
                self._token(
                    "demand",
                    requirement.demand_name,
                    requirement.skill_name,
                    requirement.bar or "any",
                    requirement.minimum_casts,
                )
            )

        for effect_name in scorecard.missing_required_effects:
            state.append(self._token("static_effect", effect_name))

        for assessment in scorecard.failed_reserve_assessments:
            requirement = assessment.requirement
            state.append(
                self._token(
                    "reserve",
                    requirement.demand_name,
                    requirement.resource.value,
                    requirement.minimum_amount,
                    assessment.available_before_start,
                    assessment.shortfall,
                )
            )

        for violation in scorecard.bar_availability_violations:
            action_kind = (
                violation.action_kind.value
                if violation.action_kind is not None
                else "none"
            )
            state.append(
                self._token(
                    "bar_legality",
                    violation.window_name,
                    self._number(violation.time_seconds),
                    action_kind,
                    violation.action_name or "none",
                    violation.reason,
                )
            )

        for violation in getattr(scorecard, "ultimate_affordability_violations", ()):
            state.append(
                self._token(
                    "ultimate_affordability",
                    violation.action_name,
                    self._number(violation.time_seconds),
                    self._number(violation.balance_before),
                    self._number(violation.required_cost),
                    self._number(violation.shortfall),
                )
            )

        for assessment in scorecard.failed_runtime_uptime_assessments:
            requirement = assessment.requirement
            state.append(
                self._token(
                    "runtime_uptime",
                    requirement.skill_name,
                    requirement.bar or "any",
                    self._number(requirement.minimum_uptime),
                    self._optional_number(assessment.observed_uptime),
                    *tuple(assessment.unresolved),
                )
            )

        if scorecard.candidate_shortfall:
            state.append(self._token("resource_shortfall", scorecard.candidate_shortfall))

        return tuple(sorted(state, key=str.casefold))

    @staticmethod
    def _token(kind: str, *parts: object) -> str:
        values = [str(kind).strip().casefold()]
        values.extend(str(part).strip() for part in parts)
        return "|".join(values)

    @staticmethod
    def _number(value: float) -> str:
        return format(float(value), ".12g")

    @classmethod
    def _optional_number(cls, value: float | None) -> str:
        return "unresolved" if value is None else cls._number(value)


__all__ = ["RotationCandidateHardObligationStateService"]
