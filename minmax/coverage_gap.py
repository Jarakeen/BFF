from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .coverage_requirement import CoverageRequirement
from .roster_coverage import CoverageProvider, CoverageReport


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

        if requirement.required_roles:
            if not (
                effect.role_relevance & requirement.required_roles
                or provider.role in requirement.required_roles
            ):
                return False

        return True
