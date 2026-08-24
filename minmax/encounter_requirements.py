from __future__ import annotations

from dataclasses import dataclass

from .coverage_requirement import CoverageRequirement
from .role import Role


@dataclass(frozen=True)
class EncounterRequirementSet:
    """
    Immutable collection of capability requirements for one encounter.

    This model describes what an encounter requires. It does not resolve
    roster capabilities, determine coverage, or recommend roster changes.
    """

    encounter_id: str
    encounter_name: str
    requirements: tuple[CoverageRequirement, ...]

    def __post_init__(self) -> None:
        if not self.encounter_id:
            raise ValueError(
                "EncounterRequirementSet.encounter_id must be non-empty."
            )

        if not self.encounter_name:
            raise ValueError(
                "EncounterRequirementSet.encounter_name must be non-empty."
            )

        effect_names = [
            requirement.effect_name
            for requirement in self.requirements
        ]

        if len(effect_names) != len(set(effect_names)):
            raise ValueError(
                "EncounterRequirementSet cannot contain duplicate "
                "effect requirements."
            )

    def all(self) -> tuple[CoverageRequirement, ...]:
        """Return every requirement in encounter order."""
        return self.requirements

    def for_effect(
        self,
        effect_name: str,
    ) -> CoverageRequirement | None:
        """Return the requirement for one effect, if present."""
        for requirement in self.requirements:
            if requirement.effect_name == effect_name:
                return requirement

        return None

    def required_effect_names(self) -> tuple[str, ...]:
        """Return the stable effect identities required by the encounter."""
        return tuple(
            requirement.effect_name
            for requirement in self.requirements
        )

    def for_role(
        self,
        role: Role,
    ) -> tuple[CoverageRequirement, ...]:
        """
        Return requirements explicitly constrained to the supplied role.

        Requirements with no role constraint are not included because they
        are encounter-wide requirements rather than role-specific ones.
        """
        return tuple(
            requirement
            for requirement in self.requirements
            if role in requirement.required_roles
        )

    @property
    def requirement_count(self) -> int:
        """Number of distinct capability requirements."""
        return len(self.requirements)
