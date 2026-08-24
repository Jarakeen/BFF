from __future__ import annotations

from dataclasses import dataclass

from .role import Role
from .support_target_type import SupportTargetType


@dataclass(frozen=True)
class CoverageRequirement:
    """
    Describes what coverage an encounter or analysis context requires.

    This is a requirement, not an observed capability. It contains no
    roster-specific information and does not determine whether the
    requirement is satisfied.
    """

    effect_name: str
    """Stable logical effect identity, e.g. 'major_slayer'."""

    target_type: SupportTargetType | None = None
    """Who must receive the effect, if the requirement is target-specific."""

    minimum_targets: int | None = None
    """Minimum number of simultaneous targets required, if applicable."""

    minimum_uptime: float | None = None
    """
    Minimum required encounter uptime as a fraction from 0.0 to 1.0,
    if the requirement specifies one.
    """

    maximum_range: float | None = None
    """Maximum distance at which the requirement must be coverable, if known."""

    required_roles: frozenset[Role] = frozenset()
    """Roles that may be required to provide this capability, if constrained."""

    condition: str | None = None
    """Named condition that must be satisfied, if applicable."""

    priority: int = 0
    """
    Relative importance of the requirement. Higher values indicate greater
    priority. The meaning of the scale belongs to the requirement source,
    not this model.
    """
    required_provider_count: int = 1
    

    def __post_init__(self) -> None:
        if not self.effect_name:
            raise ValueError("CoverageRequirement.effect_name must be non-empty.")

        if self.minimum_targets is not None and self.minimum_targets < 0:
            raise ValueError(
                "CoverageRequirement.minimum_targets cannot be negative."
            )

        if self.minimum_uptime is not None and not 0.0 <= self.minimum_uptime <= 1.0:
            raise ValueError(
                "CoverageRequirement.minimum_uptime must be between 0 and 1."
            )

        if self.maximum_range is not None and self.maximum_range < 0:
            raise ValueError(
                "CoverageRequirement.maximum_range cannot be negative."
            )
        
        if self.required_provider_count < 1:
            raise ValueError(
                "CoverageRequirement.required_provider_count must be at least 1."
            )