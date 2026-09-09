from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from services.team_provider_rotation_workload_service import (
    TeamProviderRotationWorkload,
)


_EPSILON = 1e-9


@dataclass(frozen=True)
class TeamProviderWorkloadDominance:
    """One safe dominance relationship between two viable provider alternatives."""

    preferred_id: str
    dominated_id: str
    improvements: tuple[str, ...]


@dataclass(frozen=True)
class TeamProviderWorkloadFrontierResult:
    """Non-dominated viable plans plus plans blocked before workload comparison."""

    frontier: tuple[TeamProviderRotationWorkload, ...]
    dominated: tuple[TeamProviderRotationWorkload, ...]
    blocked: tuple[TeamProviderRotationWorkload, ...]
    dominance: tuple[TeamProviderWorkloadDominance, ...]

    @property
    def frontier_ids(self) -> tuple[str, ...]:
        return tuple(item.alternative_id for item in self.frontier)


class TeamProviderWorkloadFrontierService:
    """Remove only provider plans that are unambiguously more expensive.

    Coverage and unresolved evidence remain hard gates through ``workload.viable``.
    Viable alternatives are compared only across directly comparable provider-cost
    dimensions. No weighted score is invented, so plans with genuine tradeoffs stay
    on the frontier for later encounter/role policy to choose between.

    Whole-plan heavy attacks, bar swaps, and similar execution counts are deliberately
    excluded from dominance. Those actions can also restore resources or serve other
    rotation obligations, so treating every extra occurrence as universally worse
    would collapse gameplay policy into a false scalar cost.
    """

    @classmethod
    def evaluate(
        cls,
        workloads: tuple[TeamProviderRotationWorkload, ...],
    ) -> TeamProviderWorkloadFrontierResult:
        if not workloads:
            return TeamProviderWorkloadFrontierResult((), (), (), ())

        cls._validate_comparison_scope(workloads)
        viable = tuple(item for item in workloads if item.viable)
        blocked = tuple(item for item in workloads if not item.viable)

        dominance: list[TeamProviderWorkloadDominance] = []
        dominated_ids: set[str] = set()
        for candidate in viable:
            for other in viable:
                if candidate is other:
                    continue
                improvements = cls._dominance_improvements(candidate, other)
                if improvements is None:
                    continue
                dominated_ids.add(other.alternative_id)
                dominance.append(
                    TeamProviderWorkloadDominance(
                        preferred_id=candidate.alternative_id,
                        dominated_id=other.alternative_id,
                        improvements=improvements,
                    )
                )

        frontier = tuple(
            item for item in viable if item.alternative_id not in dominated_ids
        )
        dominated = tuple(
            item for item in viable if item.alternative_id in dominated_ids
        )
        return TeamProviderWorkloadFrontierResult(
            frontier=frontier,
            dominated=dominated,
            blocked=blocked,
            dominance=tuple(dominance),
        )

    @classmethod
    def _dominance_improvements(
        cls,
        preferred: TeamProviderRotationWorkload,
        other: TeamProviderRotationWorkload,
    ) -> tuple[str, ...] | None:
        preferred_resources = dict(preferred.resource_costs)
        other_resources = dict(other.resource_costs)
        resources = sorted(set(preferred_resources) | set(other_resources))

        dimensions: list[tuple[str, float, float]] = [
            (
                "provider applications",
                float(preferred.provider_applications),
                float(other.provider_applications),
            ),
            (
                "provider GCD seconds",
                preferred.provider_gcd_seconds,
                other.provider_gcd_seconds,
            ),
            (
                "provider cast/channel seconds",
                preferred.provider_cast_channel_seconds,
                other.provider_cast_channel_seconds,
            ),
            (
                "Ultimate spend",
                preferred.ultimate_spent,
                other.ultimate_spent,
            ),
            (
                "occupied provider bar slots",
                float(preferred.occupied_bar_slot_count),
                float(other.occupied_bar_slot_count),
            ),
            (
                "primary-role displacement seconds",
                preferred.primary_role_displacement_seconds,
                other.primary_role_displacement_seconds,
            ),
        ]
        dimensions.extend(
            (
                f"{resource} spend",
                preferred_resources.get(resource, 0.0),
                other_resources.get(resource, 0.0),
            )
            for resource in resources
        )

        improvements: list[str] = []
        for label, preferred_value, other_value in dimensions:
            if preferred_value > other_value + _EPSILON:
                return None
            if preferred_value < other_value - _EPSILON:
                improvements.append(
                    f"{label}: {preferred_value:g} vs {other_value:g}"
                )

        if not improvements:
            return None
        return tuple(improvements)

    @staticmethod
    def _validate_comparison_scope(
        workloads: tuple[TeamProviderRotationWorkload, ...],
    ) -> None:
        effect_key = workloads[0].effect_key
        duration_seconds = workloads[0].duration_seconds
        seen_ids: set[str] = set()
        for workload in workloads:
            if workload.effect_key != effect_key:
                raise ValueError(
                    "provider workload frontier requires one shared effect"
                )
            if not isclose(
                workload.duration_seconds,
                duration_seconds,
                rel_tol=0.0,
                abs_tol=_EPSILON,
            ):
                raise ValueError(
                    "provider workload frontier requires one shared duration"
                )
            if workload.alternative_id in seen_ids:
                raise ValueError(
                    f"duplicate provider workload alternative_id: {workload.alternative_id}"
                )
            seen_ids.add(workload.alternative_id)


__all__ = [
    "TeamProviderWorkloadDominance",
    "TeamProviderWorkloadFrontierResult",
    "TeamProviderWorkloadFrontierService",
]
