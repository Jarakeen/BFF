from __future__ import annotations

"""Reusable raid-support coverage requirements for provider assignment.

The Coverage UI has long carried a default list of required raid effects. Phase 11
needs that requirement intent outside the UI so provider assignment can consume it
without pretending those support choices are intrinsic boss mechanics.

A profile entry only exposes a canonical capability type when an exact mapping is
already source-backed. Unmapped required entries remain explicit rather than being
converted from display text by casing/alias heuristics.
"""

from dataclasses import dataclass

from minmax.coverage_requirement import CoverageRequirement


@dataclass(frozen=True)
class RaidCoverageRequirement:
    requirement_id: str
    display_name: str
    required: bool = True
    capability_type: str | None = None
    mapping_evidence: str = ""

    def __post_init__(self) -> None:
        if not self.requirement_id:
            raise ValueError("requirement_id must be non-empty")
        if not self.display_name:
            raise ValueError("display_name must be non-empty")
        if self.capability_type is not None and not self.capability_type:
            raise ValueError("capability_type must be non-empty when supplied")
        if self.capability_type is not None and not self.mapping_evidence:
            raise ValueError("mapped coverage requirements require mapping_evidence")

    @property
    def is_mapped(self) -> bool:
        return self.capability_type is not None

    def to_coverage_requirement(self) -> CoverageRequirement | None:
        if not self.required or self.capability_type is None:
            return None
        return CoverageRequirement(effect_name=self.capability_type)


@dataclass(frozen=True)
class RaidCoverageProfile:
    profile_id: str
    name: str
    requirements: tuple[RaidCoverageRequirement, ...]

    def __post_init__(self) -> None:
        if not self.profile_id:
            raise ValueError("profile_id must be non-empty")
        if not self.name:
            raise ValueError("name must be non-empty")
        ids = [row.requirement_id for row in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("coverage profile cannot duplicate requirement_id")

    @property
    def mapped_required(self) -> tuple[RaidCoverageRequirement, ...]:
        return tuple(row for row in self.requirements if row.required and row.is_mapped)

    @property
    def unmapped_required(self) -> tuple[RaidCoverageRequirement, ...]:
        return tuple(row for row in self.requirements if row.required and not row.is_mapped)

    def coverage_requirements(self) -> tuple[CoverageRequirement, ...]:
        return tuple(
            requirement
            for row in self.requirements
            if (requirement := row.to_coverage_requirement()) is not None
        )


# Preserves the existing Coverage page's required default watch list. Only War Horn
# currently has an exact capability identity mapping proven end to end: repository-
# traced Aggressive Horn evidence resolves the EffectVariant identity ``force``.
# The remaining entries are intentionally not guessed from their display labels.
DEFAULT_RAID_COVERAGE_PROFILE = RaidCoverageProfile(
    profile_id="default_raid_coverage",
    name="Default Raid Coverage",
    requirements=(
        RaidCoverageRequirement("major_courage", "Major Courage"),
        RaidCoverageRequirement("major_vulnerability", "Major Vulnerability"),
        RaidCoverageRequirement("major_berserk", "Major Berserk"),
        RaidCoverageRequirement("major_breach", "Major Breach"),
        RaidCoverageRequirement("major_slayer", "Major Slayer"),
        RaidCoverageRequirement("crusher", "Crusher"),
        RaidCoverageRequirement("minor_brittle", "Minor Brittle"),
        RaidCoverageRequirement("minor_maim", "Minor Maim"),
        RaidCoverageRequirement(
            "war_horn",
            "War Horn",
            capability_type="force",
            mapping_evidence=(
                "Coverage UI requires War Horn; repository-traced Aggressive Horn "
                "skill evidence resolves canonical EffectVariant identity 'force'."
            ),
        ),
        RaidCoverageRequirement("orbs", "Orbs"),
        RaidCoverageRequirement("purify", "Purify"),
        RaidCoverageRequirement("magickasteal", "Magickasteal"),
        RaidCoverageRequirement("minor_resolve", "Minor Resolve"),
        RaidCoverageRequirement("minor_intellect", "Minor Intellect"),
        RaidCoverageRequirement("minor_force", "Minor Force"),
    ),
)
