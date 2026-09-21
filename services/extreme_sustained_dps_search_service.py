from __future__ import annotations

"""Search canonical saved-build witnesses for sustained DPS.

This is the first global-search orchestration layer for the saved user-state
denominator. It discovers every eligible canonical DD/DPS build with a saved
RotationPlan, evaluates them under one explicit target scenario, and preserves
all exclusions. It does not generate new builds or new rotations.
"""

from dataclasses import dataclass
from pathlib import Path

from services.extreme_sustained_dps_candidate_discovery_service import (
    ExtremeSustainedDPSCandidateDiscoveryService,
    ExtremeSustainedDPSDiscoveryResult,
)
from services.extreme_sustained_dps_comparison_service import (
    ExtremeSustainedDPSComparisonResult,
    ExtremeSustainedDPSComparisonService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSSearchResult:
    discovery: ExtremeSustainedDPSDiscoveryResult
    comparison: ExtremeSustainedDPSComparisonResult | None
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def searched_candidate_count(self) -> int:
        return self.discovery.candidate_count

    @property
    def leader(self):
        return None if self.comparison is None else self.comparison.leader

    @property
    def search_complete_for_saved_denominator(self) -> bool:
        return (
            self.comparison is not None
            and self.comparison.comparison_complete
            and not self.unresolved
        )


class ExtremeSustainedDPSSearchService:
    """Discover and compare all eligible saved DD build/rotation witnesses."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        discovery: ExtremeSustainedDPSCandidateDiscoveryService | None = None,
        comparison: ExtremeSustainedDPSComparisonService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.discovery = discovery or ExtremeSustainedDPSCandidateDiscoveryService(
            self.database_path
        )
        self.comparison = comparison or ExtremeSustainedDPSComparisonService(
            self.database_path
        )

    @staticmethod
    def _dedupe(values) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                str(value).strip()
                for value in values
                if str(value).strip()
            )
        )

    def search(
        self,
        *,
        target_health: int,
        target_resistance: float,
        target_name: str = "Boss",
    ) -> ExtremeSustainedDPSSearchResult:
        discovered = self.discovery.discover()

        unresolved: list[str] = []
        informational_exclusions: list[str] = []
        for exclusion in discovered.exclusions:
            message = f"Excluded {exclusion.label}: {exclusion.reason}"
            if bool(getattr(exclusion, "blocking", True)):
                unresolved.append(message)
            else:
                informational_exclusions.append(message)

        if discovered.candidate_count < 2:
            unresolved.append(
                "Sustained-DPS saved-state search requires at least two eligible DD/DPS builds with saved RotationPlans"
            )
            return ExtremeSustainedDPSSearchResult(
                discovery=discovered,
                comparison=None,
                evidence=tuple(discovered.evidence),
                unresolved=self._dedupe(unresolved),
            )

        comparison = self.comparison.compare(
            tuple(row.build for row in discovered.candidates),
            target_health=int(target_health),
            target_resistance=float(target_resistance),
            target_name=target_name,
        )
        unresolved.extend(comparison.unresolved)

        evidence = (
            *discovered.evidence,
            *informational_exclusions,
            *comparison.evidence,
            "Search denominator is canonical saved user-state only; no synthetic builds or rotations were generated",
        )
        return ExtremeSustainedDPSSearchResult(
            discovery=discovered,
            comparison=comparison,
            evidence=self._dedupe(evidence),
            unresolved=self._dedupe(unresolved),
        )


__all__ = [
    "ExtremeSustainedDPSSearchResult",
    "ExtremeSustainedDPSSearchService",
]
