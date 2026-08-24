from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .coverage_gap import CoverageAnalysis
from .support_stacking import StackingBehavior


class ConflictType(str, Enum):
    """Type of provider relationship discovered by conflict analysis."""

    REDUNDANCY = "redundancy"
    EXCLUSIVITY = "exclusivity"


@dataclass(frozen=True)
class ProviderConflict:
    """
    Describes a relationship between providers.

    REDUNDANCY:
        More valid providers exist than the requirement needs, and the
        effect does not explicitly stack.

    EXCLUSIVITY:
        Providers of effects sharing an explicit exclusivity group may
        compete with one another.

    `effect_name` is None for an exclusivity conflict spanning multiple
    effect identities. The exclusivity group identifies the actual
    mechanical relationship.
    """

    effect_name: str | None
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
    Analyze provider relationships preserved by CoverageAnalysis.

    Redundancy is requirement-aware:

        valid providers > required providers

    but only when the effect does not explicitly stack.

    Exclusivity is analyzed across the complete coverage analysis because
    two different effect identities can belong to the same explicit
    exclusivity group.

    This analyzer does not optimize the roster, choose winners, or invent
    ESO mechanics that are not represented by SupportEffect metadata.
    """

    def analyze(
        self,
        coverage_analysis: CoverageAnalysis,
    ) -> CoverageConflictReport:
        conflicts: list[ProviderConflict] = []

        # ---------------------------------------------------------------
        # Per-effect redundancy
        # ---------------------------------------------------------------
        for gap in coverage_analysis.gaps:
            valid_providers = gap.satisfying_provider_evidence

            if not valid_providers:
                continue

            stacking_behavior = valid_providers[0].effect.stacking

            if (
                len(valid_providers) > gap.required_provider_count
                and stacking_behavior != StackingBehavior.STACKS
            ):
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

        # ---------------------------------------------------------------
        # Cross-effect exclusivity
        # ---------------------------------------------------------------
        #
        # Exclusivity is different from redundancy. It can exist between
        # two different effect names when their explicit
        # exclusivity_group is the same.
        #
        # Only satisfying providers participate. A provider that fails
        # the encounter requirement should not create a conflict merely
        # because its underlying effect happens to share a group.
        #
        exclusivity_groups: dict[str, list[str]] = {}

        for gap in coverage_analysis.gaps:
            for provider in gap.satisfying_provider_evidence:
                group = provider.effect.exclusivity_group

                if group is None:
                    continue

                exclusivity_groups.setdefault(group, []).append(
                    provider.character_name
                )

        for group, provider_names in exclusivity_groups.items():
            unique_provider_names = tuple(dict.fromkeys(provider_names))

            if len(unique_provider_names) <= 1:
                continue

            conflicts.append(
                ProviderConflict(
                    effect_name=None,
                    conflict_type=ConflictType.EXCLUSIVITY,
                    providers=unique_provider_names,
                    exclusivity_group=group,
                )
            )

        return CoverageConflictReport(tuple(conflicts))
