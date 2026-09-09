from __future__ import annotations

from dataclasses import dataclass

from services.team_provider_rotation_workload_service import (
    TeamProviderRotationWorkload,
    TeamProviderRotationWorkloadComparison,
)


@dataclass(frozen=True)
class TeamProviderWorkloadExplanation:
    """UI-ready facts without declaring unlike workload dimensions equivalent."""

    alternative_id: str
    effect_key: str
    coverage: tuple[str, ...]
    workload: tuple[str, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class TeamProviderWorkloadComparisonExplanation:
    baseline_id: str
    candidate_id: str
    tradeoffs: tuple[str, ...]
    boundary: str


class TeamProviderWorkloadExplanationService:
    """Translate provider evidence for Comp Maker / Optimization surfaces."""

    @classmethod
    def describe(
        cls,
        result: TeamProviderRotationWorkload,
    ) -> TeamProviderWorkloadExplanation:
        coverage: list[str] = []
        recipient = result.recipient_coverage_result
        if recipient is None:
            coverage.append(
                "Recipient coverage passed."
                if result.recipient_coverage_met
                else "Recipient coverage is incomplete."
            )
        else:
            coverage.append(
                f"Recipient coverage: {recipient.covered_recipients}/"
                f"{recipient.required_recipients} recipients; "
                + (
                    "requirement met."
                    if recipient.fully_covered
                    else f"{recipient.uncovered_recipients} still uncovered."
                )
            )

        temporal = result.temporal_coverage_result
        if temporal is None:
            coverage.append(
                "Timeline coverage passed."
                if result.temporal_coverage_met
                else "Timeline coverage is incomplete."
            )
        else:
            coverage.append(
                f"Timeline coverage: {temporal.covered_seconds:g}/"
                f"{temporal.required_duration_seconds:g} seconds "
                f"({temporal.coverage_ratio:.1%}); target "
                f"{temporal.target_coverage_ratio:.1%} "
                + ("met." if temporal.target_coverage_met else "not met.")
            )
            if not temporal.distinct_source_requirement_met:
                coverage.append(
                    f"Distinct carriers: {temporal.distinct_source_count}/"
                    f"{temporal.minimum_distinct_sources}; requirement not met."
                )
            if temporal.uncovered_intervals:
                gaps = ", ".join(
                    f"{start:g}-{end:g}s"
                    for start, end in temporal.uncovered_intervals
                )
                coverage.append(f"Uncovered timeline windows: {gaps}.")

        workload = [
            f"Provider work: {result.provider_applications} applications "
            f"({result.provider_applications_per_minute:g}/minute), "
            f"{result.provider_gcd_seconds:g}s of GCD time, and "
            f"{result.provider_cast_channel_seconds:g}s casting/channeling.",
            f"Bar space: {result.occupied_bar_slot_count} occupied provider slots; "
            f"primary-role displacement: {result.primary_role_displacement_seconds:g}s.",
        ]
        if result.resource_costs:
            costs = ", ".join(
                f"{amount:g} {resource.title()}"
                for resource, amount in result.resource_costs
            )
            workload.append(f"Resource spend: {costs}.")
        if result.ultimate_spent:
            workload.append(f"Ultimate spend: {result.ultimate_spent:g}.")

        return TeamProviderWorkloadExplanation(
            alternative_id=result.alternative_id,
            effect_key=result.effect_key,
            coverage=tuple(coverage),
            workload=tuple(workload),
            blockers=result.unresolved,
        )

    @classmethod
    def compare(
        cls,
        comparison: TeamProviderRotationWorkloadComparison,
    ) -> TeamProviderWorkloadComparisonExplanation:
        deltas = (
            ("applications per minute", comparison.provider_applications_per_minute_delta),
            ("GCD seconds", comparison.provider_gcd_seconds_delta),
            ("cast/channel seconds", comparison.provider_cast_channel_seconds_delta),
            ("occupied bar slots", float(comparison.occupied_bar_slot_count_delta)),
            (
                "primary-role displacement seconds",
                comparison.primary_role_displacement_seconds_delta,
            ),
            ("Ultimate", comparison.ultimate_spent_delta),
            ("heavy attacks", float(comparison.heavy_attacks_delta)),
            ("bar swaps", float(comparison.bar_swaps_delta)),
        )
        tradeoffs = [
            cls._delta_sentence(label, delta)
            for label, delta in deltas
            if abs(delta) > 1e-9
        ]
        tradeoffs.extend(
            cls._resource_delta_sentence(resource, delta)
            for resource, delta in comparison.resource_cost_deltas
            if abs(delta) > 1e-9
        )
        if not tradeoffs:
            tradeoffs.append("The measured provider workload is unchanged.")

        return TeamProviderWorkloadComparisonExplanation(
            baseline_id=comparison.baseline.alternative_id,
            candidate_id=comparison.candidate.alternative_id,
            tradeoffs=tuple(tradeoffs),
            boundary=(
                "These are separate tradeoffs, not a universal winner; encounter and "
                "role policy decides which costs the team can best afford."
            ),
        )

    @classmethod
    def render_panel(
        cls,
        workloads: tuple[TeamProviderRotationWorkload, ...],
        *,
        comparison: TeamProviderRotationWorkloadComparison | None = None,
    ) -> str:
        """Render exact workload evidence for shared Comp/Optimization cards."""

        if not workloads:
            return (
                "No canonical provider rotation workload is attached to this team yet.\n\n"
                "Static capability availability does not prove recipient coverage, "
                "encounter uptime, sustain through the rotation, or which role can "
                "perform the job with the least disruption."
            )

        sections: list[str] = []
        for workload in workloads:
            explanation = cls.describe(workload)
            lines = [
                explanation.alternative_id.upper(),
                *explanation.coverage,
                *explanation.workload,
            ]
            if explanation.blockers:
                lines.append("Blocked / unresolved:")
                lines.extend(f"• {item}" for item in explanation.blockers)
            sections.append("\n".join(lines))

        if comparison is not None:
            if comparison.baseline not in workloads or comparison.candidate not in workloads:
                raise ValueError(
                    "provider workload comparison must reference displayed workloads"
                )
            rendered = cls.compare(comparison)
            lines = [
                f"COMPARISON • {rendered.baseline_id} → {rendered.candidate_id}",
                *(f"• {item}" for item in rendered.tradeoffs),
                rendered.boundary,
            ]
            sections.append("\n".join(lines))

        return "\n\n".join(sections)

    @staticmethod
    def _delta_sentence(label: str, delta: float) -> str:
        direction = "more" if delta > 0 else "fewer"
        amount = abs(delta)
        return f"Candidate uses {amount:g} {direction} {label}."

    @staticmethod
    def _resource_delta_sentence(resource: str, delta: float) -> str:
        direction = "more" if delta > 0 else "less"
        return f"Candidate spends {abs(delta):g} {direction} {resource.title()}."


__all__ = [
    "TeamProviderWorkloadComparisonExplanation",
    "TeamProviderWorkloadExplanation",
    "TeamProviderWorkloadExplanationService",
]
