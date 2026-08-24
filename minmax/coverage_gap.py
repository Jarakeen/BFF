from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .coverage_classification import (
    CoverageClassificationAnalyzer,
    CoverageClassificationResult,
)
from .coverage_requirement import CoverageRequirement
from .roster_coverage import CoverageProvider, CoverageReport
from .support_stacking import StackingBehavior

if TYPE_CHECKING:
    from .coverage_conflict import (
        ConflictType,
        CoverageConflictReport,
    )


class CoverageStatus(str, Enum):
    """Mechanical result for one coverage requirement."""

    COVERED = "covered"
    MISSING = "missing"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class CoverageGap:
    """
    Result of comparing one requirement against roster capability evidence.

    `providers` and `satisfying_providers` remain name-based for compatibility.

    The corresponding *_evidence fields preserve complete mechanical
    provider information for later analysis layers.
    """

    requirement: CoverageRequirement
    status: CoverageStatus

    providers: tuple[str, ...] = ()
    satisfying_providers: tuple[str, ...] = ()

    provider_evidence: tuple[CoverageProvider, ...] = ()
    satisfying_provider_evidence: tuple[CoverageProvider, ...] = ()

    @property
    def is_satisfied(self) -> bool:
        return self.status == CoverageStatus.COVERED

    @property
    def required_provider_count(self) -> int:
        return self.requirement.required_provider_count

    @property
    def valid_provider_count(self) -> int:
        return len(self.satisfying_provider_evidence)

    @property
    def redundant_provider_count(self) -> int:
        """
        Number of providers beyond the stated requirement.

        This is a mechanical count only. Whether those providers are
        actually redundant depends on the effect's stacking behavior and
        is handled by the actionable classification layer.
        """
        return max(
            0,
            self.valid_provider_count - self.required_provider_count,
        )


@dataclass(frozen=True)
class CoverageAnalysis:
    """Complete comparison of requirements against roster coverage."""

    gaps: tuple[CoverageGap, ...]

    def for_effect(self, effect_name: str) -> CoverageGap | None:
        for gap in self.gaps:
            if gap.requirement.effect_name == effect_name:
                return gap
        return None

    @property
    def missing(self) -> tuple[CoverageGap, ...]:
        return tuple(
            gap
            for gap in self.gaps
            if gap.status == CoverageStatus.MISSING
        )

    @property
    def insufficient(self) -> tuple[CoverageGap, ...]:
        return tuple(
            gap
            for gap in self.gaps
            if gap.status == CoverageStatus.INSUFFICIENT
        )

    @property
    def covered(self) -> tuple[CoverageGap, ...]:
        return tuple(
            gap
            for gap in self.gaps
            if gap.status == CoverageStatus.COVERED
        )

    def classifications(
        self,
        conflicts: CoverageConflictReport | None = None,
        *,
        resilient_providers_by_effect: dict[str, tuple[str, ...]] | None = None,
        unknown_effects: frozenset[str] = frozenset(),
    ) -> tuple[CoverageClassificationResult, ...]:
        """
        Return the actionable classification for every coverage gap.

        Coverage conflicts are interpreted conservatively:

        - REDUNDANCY remains REDUNDANT.
        - EXCLUSIVITY becomes CONFLICT.
        - No conflict preserves the ordinary coverage classification.

        Provider ordering follows the CoverageGap evidence rather than
        the internal ordering of the conflict analyzer.
        """
        analyzer = CoverageClassificationAnalyzer()
        results: list[CoverageClassificationResult] = []
        resilient_providers_by_effect = resilient_providers_by_effect or {}

        for gap in self.gaps:
            redundant_providers = self._redundant_providers(gap)
            resilient_providers = resilient_providers_by_effect.get(
                gap.requirement.effect_name,
                (),
            )

            conflicting_provider_names: set[str] = set()

            if conflicts is not None:
                from .coverage_conflict import ConflictType

                # Only EXCLUSIVITY is a mechanical conflict.
                #
                # REDUNDANCY is deliberately ignored here because it is
                # already represented by the REDUNDANT classification.
                for conflict in conflicts.exclusivities:
                    conflict_provider_names = set(conflict.providers)

                    gap_provider_names = {
                        provider.character_name
                        for provider in gap.provider_evidence
                    }

                    conflicting_provider_names.update(
                        conflict_provider_names & gap_provider_names
                    )

            # Preserve canonical CoverageGap provider ordering.
            conflicting_providers = tuple(
                provider.character_name
                for provider in gap.provider_evidence
                if provider.character_name in conflicting_provider_names
            )

            results.append(
                analyzer.classify(
                    effect_name=gap.requirement.effect_name,
                    required_provider_count=gap.required_provider_count,
                    providers=gap.providers,
                    satisfying_providers=gap.satisfying_providers,
                    redundant_providers=redundant_providers,
                    resilient_providers=resilient_providers,
                    conflicting_providers=conflicting_providers,
                    evidence_sufficient=gap.requirement.effect_name not in unknown_effects,
                )
            )

        return tuple(results)

    def classification_for_effect(
        self,
        effect_name: str,
        conflicts: CoverageConflictReport | None = None,
    ) -> CoverageClassificationResult | None:
        """Return the actionable classification for one effect."""
        for classification in self.classifications(conflicts):
            if classification.effect_name == effect_name:
                return classification

        return None

    @staticmethod
    def _redundant_providers(
        gap: CoverageGap,
    ) -> tuple[str, ...]:
        """
        Determine which satisfying providers are genuinely redundant under
        the current requirement and effect stacking behavior.

        STACKS effects are never automatically classified as redundant,
        because multiple providers may contribute simultaneously.

        UNIQUE and HIGHEST_ONLY effects can have providers beyond the
        required count classified as redundant.
        """
        satisfying = gap.satisfying_provider_evidence

        if not satisfying:
            return ()

        if any(
            provider.effect.stacking == StackingBehavior.STACKS
            for provider in satisfying
        ):
            return ()

        if len(satisfying) <= gap.required_provider_count:
            return ()

        return tuple(
            provider.character_name
            for provider in satisfying[gap.required_provider_count:]
        )


class CoverageGapAnalyzer:
    """
    Compare requirements against roster capability evidence.

    Coverage is satisfied when the number of mechanically valid providers
    meets the requirement's required_provider_count.
    """

    def analyze(
        self,
        coverage: CoverageReport,
        requirements: tuple[CoverageRequirement, ...],
    ) -> CoverageAnalysis:
        results: list[CoverageGap] = []

        for requirement in requirements:
            entry = coverage.for_effect(requirement.effect_name)

            if entry is None or not entry.providers:
                results.append(
                    CoverageGap(
                        requirement=requirement,
                        status=CoverageStatus.MISSING,
                    )
                )
                continue

            satisfying = tuple(
                provider
                for provider in entry.providers
                if self._satisfies(provider, requirement)
            )

            status = (
                CoverageStatus.COVERED
                if len(satisfying) >= requirement.required_provider_count
                else CoverageStatus.INSUFFICIENT
            )

            results.append(
                CoverageGap(
                    requirement=requirement,
                    status=status,
                    providers=tuple(
                        provider.character_name
                        for provider in entry.providers
                    ),
                    satisfying_providers=tuple(
                        provider.character_name
                        for provider in satisfying
                    ),
                    provider_evidence=entry.providers,
                    satisfying_provider_evidence=satisfying,
                )
            )

        return CoverageAnalysis(tuple(results))


    @staticmethod
    def _satisfies(
        provider: CoverageProvider,
        requirement: CoverageRequirement,
    ) -> bool:
        effect = provider.effect

        if requirement.target_type is not None:
            if effect.target_type != requirement.target_type:
                return False

        if requirement.minimum_targets is not None:
            if effect.target_count is None:
                return False
            if effect.target_count < requirement.minimum_targets:
                return False

        if requirement.maximum_range is not None:
            if effect.range is None:
                return False
            if effect.range < requirement.maximum_range:
                return False

        if requirement.minimum_uptime is not None:
            if effect.uptime < requirement.minimum_uptime:
                return False

        if requirement.required_roles:
            if not (
                effect.role_relevance & requirement.required_roles
                or provider.role in requirement.required_roles
            ):
                return False

        return True
