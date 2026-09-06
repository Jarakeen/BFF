from __future__ import annotations

from dataclasses import dataclass

from services.team_optimization_canonical_analysis import TeamOptimizationCanonicalAnalysis


@dataclass(frozen=True)
class TeamOptimizationStaticComparison:
    """Bounded Phase 12.5 comparison of two canonical static team analyses.

    This comparison intentionally does not choose a raid winner. It compares only
    evidence already resolved by the static capability layer: capability presence,
    provider redundancy, recruit/open chairs, unresolved capability gaps,
    conditional sources, and explicit evidence boundaries.
    """

    team_a: TeamOptimizationCanonicalAnalysis
    team_b: TeamOptimizationCanonicalAnalysis
    shared_capabilities: tuple[str, ...]
    team_a_only_capabilities: tuple[str, ...]
    team_b_only_capabilities: tuple[str, ...]
    team_a_redundant_capabilities: tuple[tuple[str, int], ...]
    team_b_redundant_capabilities: tuple[tuple[str, int], ...]

    @property
    def team_a_redundancy_count(self) -> int:
        return len(self.team_a_redundant_capabilities)

    @property
    def team_b_redundancy_count(self) -> int:
        return len(self.team_b_redundant_capabilities)


class TeamOptimizationStaticComparisonService:
    """Compare two static canonical analyses without encounter-aware ranking."""

    @staticmethod
    def _capability_map(
        analysis: TeamOptimizationCanonicalAnalysis,
    ) -> dict[str, tuple[str, ...]]:
        return dict(analysis.capability_providers)

    def compare(
        self,
        team_a: TeamOptimizationCanonicalAnalysis,
        team_b: TeamOptimizationCanonicalAnalysis,
    ) -> TeamOptimizationStaticComparison:
        providers_a = self._capability_map(team_a)
        providers_b = self._capability_map(team_b)
        names_a = set(providers_a)
        names_b = set(providers_b)

        redundant_a = tuple(
            (name, len(providers))
            for name, providers in sorted(providers_a.items(), key=lambda item: item[0].casefold())
            if len(providers) > 1
        )
        redundant_b = tuple(
            (name, len(providers))
            for name, providers in sorted(providers_b.items(), key=lambda item: item[0].casefold())
            if len(providers) > 1
        )

        return TeamOptimizationStaticComparison(
            team_a=team_a,
            team_b=team_b,
            shared_capabilities=tuple(sorted(names_a & names_b, key=str.casefold)),
            team_a_only_capabilities=tuple(sorted(names_a - names_b, key=str.casefold)),
            team_b_only_capabilities=tuple(sorted(names_b - names_a, key=str.casefold)),
            team_a_redundant_capabilities=redundant_a,
            team_b_redundant_capabilities=redundant_b,
        )
