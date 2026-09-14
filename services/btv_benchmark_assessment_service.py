from __future__ import annotations

from dataclasses import dataclass

from .btv_benchmark_evidence_service import (
    BTVBenchmarkCorpus,
    BTVBenchmarkObservation,
    UPTIME_DENOMINATOR_UNKNOWN,
)
from .team_provider_temporal_coverage_service import TeamProviderTemporalCoverageResult
from .team_provider_uptime_policy_service import (
    TeamProviderUptimeAssessment,
    TeamProviderUptimePolicyService,
)


@dataclass(frozen=True)
class BTVBenchmarkTemporalAssessment:
    """Compare one planned provider window with one scoped BTV benchmark row.

    BTVTools observations remain calibration evidence.  The screenshot target may be
    reused as encounter-scoped strategy policy, but the screenshot's observed uptime
    is compared with BFF temporal output only when the caller proves both values use
    the same denominator basis.
    """

    observation: BTVBenchmarkObservation
    temporal_result: TeamProviderTemporalCoverageResult
    uptime_assessment: TeamProviderUptimeAssessment | None
    benchmark_observed_comparison_allowed: bool
    benchmark_observed_delta_ratio: float | None
    theoretical_excess_ratio: float | None
    feedback: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def target_met(self) -> bool | None:
        if self.uptime_assessment is None:
            return None
        return self.uptime_assessment.target_met


class BTVBenchmarkAssessmentService:
    """Apply scoped BTV benchmark evidence to existing provider timing results.

    This service deliberately does not calculate provider uptime itself.  Timing,
    merged coverage, overlap, and uncovered intervals remain owned by
    ``TeamProviderTemporalCoverageService``.  This layer selects benchmark policy,
    validates scope, and turns those existing results into calibration feedback.
    """

    @staticmethod
    def _canonical(value: object) -> str:
        return "_".join(str(value or "").strip().casefold().replace("-", " ").split())

    @classmethod
    def select_target_observation(
        cls,
        corpus: BTVBenchmarkCorpus,
        *,
        effect_key: str,
        page: str = "insights",
        player_role: str | None = None,
    ) -> BTVBenchmarkObservation | None:
        """Return one unambiguous target-bearing benchmark row for a scoped effect.

        Player-scoped buff-page observations must not silently replace group-level
        Insights targets for the same named effect.
        """
        rows = corpus.find(
            effect_key=effect_key,
            page=page,
            player_role=player_role,
        )
        candidates = tuple(row for row in rows if row.target_ratio is not None)
        if not candidates:
            return None
        if len(candidates) > 1:
            scopes = ", ".join(
                f"{row.page}/{row.player_role or 'group'}:{row.source_file}"
                for row in candidates
            )
            raise ValueError(
                f"ambiguous BTV benchmark target for {effect_key!r}: {scopes}"
            )
        return candidates[0]

    @classmethod
    def assess_temporal_result(
        cls,
        observation: BTVBenchmarkObservation,
        temporal_result: TeamProviderTemporalCoverageResult,
        *,
        temporal_uptime_denominator_basis: str = UPTIME_DENOMINATOR_UNKNOWN,
    ) -> BTVBenchmarkTemporalAssessment:
        if cls._canonical(observation.effect_key) != cls._canonical(
            temporal_result.effect_key
        ):
            raise ValueError(
                "benchmark effect_key must match temporal coverage effect_key"
            )

        policy = observation.to_uptime_policy()
        uptime_assessment = None
        if policy is not None:
            uptime_assessment = TeamProviderUptimePolicyService.assess(
                policy,
                observed_ratio=temporal_result.coverage_ratio,
            )

        theoretical_excess = None
        if observation.theoretical_max_ratio is not None:
            theoretical_excess = max(
                0.0,
                float(temporal_result.coverage_ratio)
                - float(observation.theoretical_max_ratio),
            )

        same_known_denominator = (
            observation.uptime_denominator_basis != UPTIME_DENOMINATOR_UNKNOWN
            and temporal_uptime_denominator_basis != UPTIME_DENOMINATOR_UNKNOWN
            and observation.uptime_denominator_basis
            == temporal_uptime_denominator_basis
        )
        observed_delta = None
        if same_known_denominator and observation.observed_ratio is not None:
            observed_delta = (
                float(temporal_result.coverage_ratio)
                - float(observation.observed_ratio)
            )

        feedback: list[str] = []
        unresolved: list[str] = []

        planned_percent = temporal_result.coverage_ratio * 100.0
        if uptime_assessment is not None:
            target_percent = uptime_assessment.policy.target_percent
            if uptime_assessment.target_met:
                feedback.append(
                    f"Planned {observation.effect_key} uptime {planned_percent:.1f}% meets "
                    f"the scoped BTV target {target_percent:.1f}%."
                )
            else:
                feedback.append(
                    f"Planned {observation.effect_key} uptime {planned_percent:.1f}% is "
                    f"{uptime_assessment.shortfall_percent:.1f} percentage points below "
                    f"the scoped BTV target {target_percent:.1f}%."
                )
        elif observation.theoretical_max_ratio is not None:
            feedback.append(
                f"BTV provides no target for {observation.effect_key}; the visible "
                f"theoretical maximum is {observation.theoretical_max_ratio * 100.0:.1f}%."
            )
        else:
            unresolved.append(
                "Benchmark row has neither a target ratio nor a theoretical maximum."
            )

        if temporal_result.uncovered_intervals:
            rendered_gaps = ", ".join(
                f"{left:.1f}-{right:.1f}s"
                for left, right in temporal_result.uncovered_intervals
            )
            feedback.append(
                f"Uncovered provider time totals {temporal_result.uncovered_seconds:.1f}s "
                f"across {rendered_gaps}."
            )
        else:
            feedback.append("No uncovered provider time remains in the required window.")

        if temporal_result.simultaneous_overlap_seconds > 1e-9:
            feedback.append(
                f"Provider applications overlap for "
                f"{temporal_result.simultaneous_overlap_seconds:.1f}s; overlap is reported "
                "as a diagnostic and is not automatically treated as waste."
            )

        if theoretical_excess is not None and theoretical_excess > 1e-9:
            unresolved.append(
                f"Planned uptime exceeds the screenshot theoretical maximum by "
                f"{theoretical_excess * 100.0:.1f} percentage points; denominator or "
                "scope evidence must be reconciled before comparison."
            )

        if observation.observed_ratio is not None and not same_known_denominator:
            unresolved.append(
                "Screenshot-observed uptime is not numerically compared with BFF planned "
                "uptime because the two denominator bases are not both known and equal."
            )
        elif observed_delta is not None:
            direction = "above" if observed_delta >= 0 else "below"
            feedback.append(
                f"Planned uptime is {abs(observed_delta) * 100.0:.1f} percentage points "
                f"{direction} the screenshot observation on the same denominator basis."
            )

        return BTVBenchmarkTemporalAssessment(
            observation=observation,
            temporal_result=temporal_result,
            uptime_assessment=uptime_assessment,
            benchmark_observed_comparison_allowed=same_known_denominator,
            benchmark_observed_delta_ratio=observed_delta,
            theoretical_excess_ratio=theoretical_excess,
            feedback=tuple(feedback),
            unresolved=tuple(unresolved),
        )
