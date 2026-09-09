from __future__ import annotations

from dataclasses import dataclass

from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_support_cadence_progression_runner_service import (
    RotationSupportCadenceProgressionRun,
    RotationSupportCadenceProgressionStopReason,
)


@dataclass(frozen=True)
class RotationSupportCadenceProgressionStepReport:
    iteration: int
    seed_build_name: str
    candidate_count: int
    eligible_candidate_count: int
    ineligible_candidate_count: int
    promoted_candidate_id: str | None
    promoted_rationale: str | None
    promoted_reasons: tuple[str, ...]
    accepted: bool
    unresolved: tuple[str, ...]

    @property
    def advanced(self) -> bool:
        return self.accepted


@dataclass(frozen=True)
class RotationSupportCadenceProgressionReport:
    """UI-safe explanation of an already-completed cadence progression run."""

    initial_build_name: str
    final_build_name: str
    iterations: int
    advanced_steps: int
    stop_reason: RotationSupportCadenceProgressionStopReason
    stop_summary: str
    steps: tuple[RotationSupportCadenceProgressionStepReport, ...]
    unresolved: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return self.advanced_steps > 0


class RotationSupportCadenceProgressionReportService:
    """Explain progression results without scoring or changing engine decisions."""

    def build(
        self,
        run: RotationSupportCadenceProgressionRun,
    ) -> RotationSupportCadenceProgressionReport:
        reports: list[RotationSupportCadenceProgressionStepReport] = []
        final_iteration = len(run.steps)
        for iteration, step in enumerate(run.steps, start=1):
            eligible = sum(
                1 for item in step.ranking if item.tier is RotationCandidateTier.ELIGIBLE
            )
            ineligible = len(step.ranking) - eligible

            promoted_rationale: str | None = None
            promoted_reasons: tuple[str, ...] = ()
            promoted_id = step.promoted_candidate_id
            if promoted_id is not None:
                promoted = step.recommendation.recommended
                if promoted is None:
                    raise ValueError(
                        "advanced cadence progression step is missing its recommendation"
                    )
                if promoted.candidate_id.casefold() != promoted_id.casefold():
                    raise ValueError(
                        "cadence progression promoted candidate does not match recommendation"
                    )
                promoted_rationale = promoted.rationale
                promoted_reasons = tuple(promoted.reasons)

            accepted = promoted_id is not None
            if (
                accepted
                and run.stop_reason is RotationSupportCadenceProgressionStopReason.REPEATED_PLAN
                and iteration == final_iteration
            ):
                accepted = False

            reports.append(
                RotationSupportCadenceProgressionStepReport(
                    iteration=iteration,
                    seed_build_name=step.seed_plan.build_name,
                    candidate_count=len(step.neighborhood.candidates),
                    eligible_candidate_count=eligible,
                    ineligible_candidate_count=ineligible,
                    promoted_candidate_id=promoted_id,
                    promoted_rationale=promoted_rationale,
                    promoted_reasons=promoted_reasons,
                    accepted=accepted,
                    unresolved=tuple(step.unresolved),
                )
            )

        return RotationSupportCadenceProgressionReport(
            initial_build_name=run.initial_plan.build_name,
            final_build_name=run.final_plan.build_name,
            iterations=run.iterations,
            advanced_steps=run.advanced_steps,
            stop_reason=run.stop_reason,
            stop_summary=self._stop_summary(run.stop_reason),
            steps=tuple(reports),
            unresolved=tuple(run.unresolved),
        )

    @staticmethod
    def _stop_summary(reason: RotationSupportCadenceProgressionStopReason) -> str:
        if reason is RotationSupportCadenceProgressionStopReason.NO_PROMOTION:
            return "No eligible local cadence candidate improved the accepted rotation."
        if reason is RotationSupportCadenceProgressionStopReason.REPEATED_PLAN:
            return "The next promoted candidate repeated an already accepted executable schedule."
        if reason is RotationSupportCadenceProgressionStopReason.MAX_ITERATIONS:
            return "The configured progression iteration limit was reached."
        raise ValueError(f"unsupported support cadence progression stop reason: {reason!r}")


__all__ = [
    "RotationSupportCadenceProgressionReport",
    "RotationSupportCadenceProgressionReportService",
    "RotationSupportCadenceProgressionStepReport",
]
