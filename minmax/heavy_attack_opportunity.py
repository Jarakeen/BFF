from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .heavy_attack_restoration import HeavyAttackWeaponType, resource_for_heavy_attack_weapon
from .resource_costs import ResourceType


class HeavyAttackPurpose(str, Enum):
    RECOVERY = "recovery"
    REQUIRED_EFFECT = "required_effect"


@dataclass(frozen=True)
class HeavyAttackOpportunityEvidence:
    """Caller-proven evidence for one possible fully charged heavy attack.

    A heavy can be considered either because sustain needs resource recovery or
    because an explicit build/set/skill effect requires a heavy attack. This layer
    does not infer those requirements from names. The caller must supply that
    evidence, along with timing and encounter safety.
    """

    weapon: HeavyAttackWeaponType
    purpose: HeavyAttackPurpose
    available_window_seconds: float
    required_window_seconds: float
    encounter_allows_channel: bool = True
    higher_priority_action_ready: bool = False
    refresh_due_before_completion: bool = False
    requirement_name: str | None = None
    needed_resource: ResourceType | None = None
    current_resource: float | None = None
    maximum_resource: float | None = None
    recovery_trigger_fraction: float = 0.0

    def __post_init__(self) -> None:
        purpose = self.purpose if isinstance(self.purpose, HeavyAttackPurpose) else HeavyAttackPurpose(str(self.purpose))
        object.__setattr__(self, "purpose", purpose)

        available = float(self.available_window_seconds)
        required = float(self.required_window_seconds)
        for name, value in (
            ("available_window_seconds", available),
            ("required_window_seconds", required),
        ):
            if not math.isfinite(value):
                raise ValueError(f"heavy attack opportunity {name} must be finite")
        if available < 0:
            raise ValueError("heavy attack available window cannot be negative")
        if required <= 0:
            raise ValueError("heavy attack required window must be positive")

        if self.requirement_name is not None:
            name = str(self.requirement_name).strip()
            object.__setattr__(self, "requirement_name", name or None)

        if purpose is HeavyAttackPurpose.REQUIRED_EFFECT:
            if not self.requirement_name:
                raise ValueError("required-effect heavy attack needs a requirement name")
            return

        if self.needed_resource is None:
            raise ValueError("recovery heavy attack needs a resource type")
        if self.current_resource is None or self.maximum_resource is None:
            raise ValueError("recovery heavy attack needs current and maximum resource values")

        current = float(self.current_resource)
        maximum = float(self.maximum_resource)
        trigger = float(self.recovery_trigger_fraction)
        for name, value in (
            ("current_resource", current),
            ("maximum_resource", maximum),
            ("recovery_trigger_fraction", trigger),
        ):
            if not math.isfinite(value):
                raise ValueError(f"heavy attack opportunity {name} must be finite")
        if maximum <= 0:
            raise ValueError("heavy attack opportunity maximum_resource must be positive")
        if current < 0:
            raise ValueError("heavy attack opportunity current_resource cannot be negative")
        if not 0 <= trigger <= 1:
            raise ValueError("heavy attack recovery trigger fraction must be between 0 and 1")


@dataclass(frozen=True)
class HeavyAttackOpportunity:
    recommended: bool
    reason: str
    purpose: HeavyAttackPurpose
    resource_fraction: float | None = None


def evaluate_heavy_attack_opportunity(
    evidence: HeavyAttackOpportunityEvidence,
) -> HeavyAttackOpportunity:
    """Return whether the supplied window is suitable for the explicit heavy purpose."""

    if not evidence.encounter_allows_channel:
        return HeavyAttackOpportunity(
            recommended=False,
            reason="encounter evidence does not allow a safe channel window",
            purpose=evidence.purpose,
        )
    if evidence.available_window_seconds < evidence.required_window_seconds:
        return HeavyAttackOpportunity(
            recommended=False,
            reason=(
                f"available window {evidence.available_window_seconds:g}s is shorter than required "
                f"heavy-attack window {evidence.required_window_seconds:g}s"
            ),
            purpose=evidence.purpose,
        )
    if evidence.refresh_due_before_completion:
        return HeavyAttackOpportunity(
            recommended=False,
            reason="a verified refresh obligation becomes due before the heavy attack completes",
            purpose=evidence.purpose,
        )

    if evidence.purpose is HeavyAttackPurpose.REQUIRED_EFFECT:
        if evidence.higher_priority_action_ready:
            return HeavyAttackOpportunity(
                recommended=False,
                reason=(
                    f"required heavy for {evidence.requirement_name} is ready, but a higher-priority "
                    "legal rotation action currently takes precedence"
                ),
                purpose=evidence.purpose,
            )
        return HeavyAttackOpportunity(
            recommended=True,
            reason=f"heavy attack is required to maintain or trigger {evidence.requirement_name}",
            purpose=evidence.purpose,
        )

    fraction = min(1.0, float(evidence.current_resource) / float(evidence.maximum_resource))
    restored_resource = resource_for_heavy_attack_weapon(evidence.weapon)
    assert evidence.needed_resource is not None

    if restored_resource is not evidence.needed_resource:
        return HeavyAttackOpportunity(
            recommended=False,
            reason=(
                f"{evidence.weapon.value} heavy attack restores {restored_resource.value}, "
                f"not required {evidence.needed_resource.value}"
            ),
            purpose=evidence.purpose,
            resource_fraction=fraction,
        )
    if fraction > evidence.recovery_trigger_fraction:
        return HeavyAttackOpportunity(
            recommended=False,
            reason=(
                f"resource fraction {fraction:.3f} is above recovery trigger "
                f"{evidence.recovery_trigger_fraction:.3f}"
            ),
            purpose=evidence.purpose,
            resource_fraction=fraction,
        )
    if evidence.higher_priority_action_ready:
        return HeavyAttackOpportunity(
            recommended=False,
            reason="a higher-priority legal rotation action is ready",
            purpose=evidence.purpose,
            resource_fraction=fraction,
        )

    return HeavyAttackOpportunity(
        recommended=True,
        reason=(
            f"safe {evidence.available_window_seconds:g}s recovery window with "
            f"{evidence.needed_resource.value} at {fraction:.1%}"
        ),
        purpose=evidence.purpose,
        resource_fraction=fraction,
    )
