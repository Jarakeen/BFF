from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .coverage_requirement import CoverageRequirement
from .roster_coverage import CoverageReport
from .support_effect import SupportEffect
from .support_target_type import SupportTargetType


class CoverageStatus(str, Enum):
    """Mechanical result for one coverage requirement."""

    COVERED = "covered"
    MISSING = "missing"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class CoverageGap:
    """
    Result of comparing one requirement against roster capability evidence.

    A requirement is COVERED only when at least one provider satisfies all
    mechanical constraints represented by the requirement.

    MISSING means no provider exists.

    INSUFFICIENT means providers exist, but none satisfy the requirement.
    """

    requirement: CoverageRequirement
    status: CoverageStatus
    providers: tuple[str, ...] = ()
    satisfying_providers: tuple[str, ...] = ()

    @property
    def is_satisfied(self) -> bool:
        return self.status == CoverageStatus.COVERED


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
            gap for gap in self.gaps
            if gap.status == CoverageStatus.MISSING
        )

    @property
    def insufficient(self) -> tuple[CoverageGap, ...]:
        return tuple(
            gap for gap in self.gaps
            if gap.status == CoverageStatus.INSUFFICIENT
        )

    @property
    def covered(self) -> tuple[CoverageGap, ...]:
        return tuple(
            gap for gap in self.gaps
            if gap.status == CoverageStatus.COVERED
        )


class CoverageGapAnalyzer:
    """
    Compare requirements against roster capability evidence.

    This layer evaluates only mechanical constraints explicitly represented
    by CoverageRequirement. It does not optimize the roster and does not
    infer encounter-specific rules.
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

            providers = tuple(
                provider.character_name
                for provider in entry.providers
            )

            satisfying = tuple(
                provider.character_name
                for provider in entry.providers
                if self._satisfies(
                    provider.effect,
                    requirement,
                )
            )

            if satisfying:
                status = CoverageStatus.COVERED
            else:
                status = CoverageStatus.INSUFFICIENT

            results.append(
                CoverageGap(
                    requirement=requirement,
                    status=status,
                    providers=providers,
                    satisfying_providers=satisfying,
                )
            )

        return CoverageAnalysis(tuple(results))

    @staticmethod
    def _satisfies(
        effect: SupportEffect,
        requirement: CoverageRequirement,
    ) -> bool:
        if not CoverageGapAnalyzer._target_type_matches(
            effect,
            requirement,
        ):
            return False

        if not CoverageGapAnalyzer._target_count_matches(
            effect,
            requirement,
        ):
            return False

        if not CoverageGapAnalyzer._range_matches(
            effect,
            requirement,
        ):
            return False

        if not CoverageGapAnalyzer._role_constraint_is_possible(
            effect,
            requirement,
        ):
            return False

        return True

    @staticmethod
    def _target_type_matches(
        effect: SupportEffect,
        requirement: CoverageRequirement,
    ) -> bool:
        if requirement.target_type is None:
            return True

        return effect.target_type == requirement.target_type

    @staticmethod
    def _target_count_matches(
        effect: SupportEffect,
        requirement: CoverageRequirement,
    ) -> bool:
        if requirement.minimum_targets is None:
            return True

        if effect.target_count is None:
            return False

        return effect.target_count >= requirement.minimum_targets

    @staticmethod
    def _range_matches(
        effect: SupportEffect,
        requirement: CoverageRequirement,
    ) -> bool:
        if requirement.maximum_range is None:
            return True

        if effect.range is None:
            return False

        return effect.range >= requirement.maximum_range

    @staticmethod
    def _role_constraint_is_possible(
        effect: SupportEffect,
        requirement: CoverageRequirement,
    ) -> bool:
        if not requirement.required_roles:
            return True

        return bool(effect.role_relevance & requirement.required_roles)
