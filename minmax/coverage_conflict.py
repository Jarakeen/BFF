from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .coverage_gap import CoverageAnalysis


class ConflictType(str, Enum):
    """Type of provider relationship discovered by conflict analysis."""

    REDUNDANCY = "redundancy"
    EXCLUSIVITY = "exclusivity"


@dataclass(frozen=True)
class ProviderConflict:
    """
    Describes a relationship between providers of the same capability.

    REDUNDANCY means more valid providers exist than the requirement needs.

    EXCLUSIVITY means multiple valid providers share an explicit
    exclusivity group. This is reported as evidence only; the analyzer
    does not decide which provider wins.
    """

    effect_name: str
    conflict_type: ConflictType
    providers: tuple[str, ...]
    exclusivity_group: str | None = None


@dataclass(frozen=True)
class CoverageConflictReport:
    """Results of provider redundancy and exclusivity analysis."""

    conflicts: tuple[ProviderConflict, ...]

    @property
    def redundancies(self) -> tuple[ProviderConflict, ...]:
        return tuple(
            conflict
            for conflict in self.conflicts
            if conflict.conflict_type == ConflictType.REDUNDANCY
        )

    @property
    def exclusivities(self) -> tuple[ProviderConflict, ...]:
        return tuple(
            conflict
            for conflict in self.conflicts
            if conflict.conflict_type == ConflictType.EXCLUSIVITY
        )

    def for_effect(
        self,
        effect_name: str,
    ) -> tuple[ProviderConflict, ...]:
        return tuple(
            conflict
            for conflict in self.conflicts
            if conflict.effect_name == effect_name
        )


class CoverageConflictAnalyzer:
    """
    Analyze provider relationships already preserved by CoverageAnalysis.

    Redundancy is requirement-aware:

        valid providers > required providers

    Therefore two Major Courage providers are redundant when one is
    required, but two providers are not redundant when two are required.

    This analyzer does not optimize the roster, remove providers, choose
    winners, or invent stacking rules.
    """

    def analyze(
        self,
        coverage_analysis: CoverageAnalysis,
    ) -> CoverageConflictReport:
        conflicts: list[ProviderConflict] = []

        for gap in coverage_analysis.gaps:
            valid_providers = gap.satisfying_provider_evidence

            # Redundancy only exists when there are more valid providers
            # than the requirement actually needs.
            if len(valid_providers) > gap.required_provider_count:
                redundant = valid_providers[gap.required_provider_count:]

                conflicts.append(
                    ProviderConflict(
                        effect_name=gap.requirement.effect_name,
                        conflict_type=ConflictType.REDUNDANCY,
                        providers=tuple(
                            provider.character_name
                            for provider in redundant
                        ),
                    )
                )

            # Exclusivity is only meaningful among providers that actually
            # satisfy the requirement.
            exclusivity_groups: dict[str, list[str]] = {}

            for provider in valid_providers:
                group = provider.effect.exclusivity_group

                if group is None:
                    continue

                exclusivity_groups.setdefault(group, []).append(
                    provider.character_name
                )

            for group, provider_names in exclusivity_groups.items():
                if len(provider_names) > 1:
                    conflicts.append(
                        ProviderConflict(
                            effect_name=gap.requirement.effect_name,
                            conflict_type=ConflictType.EXCLUSIVITY,
                            providers=tuple(provider_names),
                            exclusivity_group=group,
                        )
                    )

        return CoverageConflictReport(tuple(conflicts))
