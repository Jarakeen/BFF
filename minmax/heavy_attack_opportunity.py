from __future__ import annotations

from dataclasses import dataclass
import math

from .heavy_attack_restoration import HeavyAttackWeaponType, resource_for_heavy_attack_weapon
from .resource_costs import ResourceType


@dataclass(frozen=True)
class HeavyAttackOpportunityEvidence:
    """Caller-proven evidence for one possible fully charged heavy attack.

    This contract decides only whether a heavy attack is a sensible recovery
    opportunity. It does not invent weapon channel times, resource-return values,
    encounter safety, or ability priority. Those facts must be supplied by the
    existing timing, sustain, encounter, and priority layers.
    """

    weapon: HeavyAttackWeaponType
    needed_resource: ResourceType
    current_resource: float
    maximum_resource: float
    recovery_trigger_fraction: float
    available_window_seconds: float
    required_window_seconds: float
    higher_priority_action_ready: bool = False
    refresh_due_before_completion: bool = False
    encounter_allows_channel: bool = True

    def __post_init__(self) -> None:
        current = float(self.current_resource)
        maximum = float(self.maximum_resource)
        trigger = float(self.recovery_trigger_fraction)
        available = float(self.available_window_seconds)
        required = float(self.required_window_seconds)
        for name, value in (
            ("current_resource", current),
            ("maximum_resource", maximum),
            ("recovery_trigger_fraction", trigger),
            ("available_window_seconds", available),
            ("required_window_seconds", required),
        ):
            if not math.isfinite(value):
                raise ValueError(f"heavy attack opportunity {name} must be finite")
        if maximum <= 0:
            raise ValueError("heavy attack opportunity maximum_resource must be positive")
        if current < 0:
            raise ValueError("heavy attack opportunity current_resource cannot be negative")
        if not 0 <= trigger <= 1:
            raise ValueError("heavy attack recovery trigger fraction must be between 0 and 1")
        if available < 0:
            raise ValueError("heavy attack available window cannot be negative")
        if required <= 0:
            raise ValueError("heavy attack required window must be positive")


@dataclass(frozen=True)
class HeavyAttackOpportunity:
    recommended: bool
    reason: str
    resource_fraction: float


def evaluate_heavy_attack_opportunity(
    evidence: HeavyAttackOpportunityEvidence,
) -> HeavyAttackOpportunity:
    """Return whether the supplied window is suitable for a recovery heavy attack."""

    fraction = min(1.0, evidence.current_resource / evidence.maximum_resource)
    restored_resource = resource_for_heavy_attack_weapon(evidence.weapon)

    if restored_resource is not evidence.needed_resource:
        return HeavyAttackOpportunity(
            recommended=False,
            reason=(
                f"{evidence.weapon.value} heavy attack restores {restored_resource.value}, "
                f"not required {evidence.needed_resource.value}"
            ),
            resource_fraction=fraction,
        )
    if fraction > evidence.recovery_trigger_fraction:
        return HeavyAttackOpportunity(
            recommended=False,
            reason=(
                f"resource fraction {fraction:.3f} is above recovery trigger "
                f"{evidence.recovery_trigger_fraction:.3f}"
            ),
            resource_fraction=fraction,
        )
    if evidence.higher_priority_action_ready:
        return HeavyAttackOpportunity(
            recommended=False,
            reason="a higher-priority legal rotation action is ready",
            resource_fraction=fraction,
        )
    if evidence.refresh_due_before_completion:
        return HeavyAttackOpportunity(
            recommended=False,
            reason="a verified refresh obligation becomes due before the heavy attack completes",
            resource_fraction=fraction,
        )
    if not evidence.encounter_allows_channel:
        return HeavyAttackOpportunity(
            recommended=False,
            reason="encounter evidence does not allow a safe channel window",
            resource_fraction=fraction,
        )
    if evidence.available_window_seconds < evidence.required_window_seconds:
        return HeavyAttackOpportunity(
            recommended=False,
            reason=(
                f"available window {evidence.available_window_seconds:g}s is shorter than required "
                f"heavy-attack window {evidence.required_window_seconds:g}s"
            ),
            resource_fraction=fraction,
        )

    return HeavyAttackOpportunity(
        recommended=True,
        reason=(
            f"safe {evidence.available_window_seconds:g}s recovery window with "
            f"{evidence.needed_resource.value} at {fraction:.1%}"
        ),
        resource_fraction=fraction,
    )
