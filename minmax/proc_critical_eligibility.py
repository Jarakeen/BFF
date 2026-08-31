from __future__ import annotations

"""Critical-eligibility policy for proc/set damage and healing effects.

This module is intentionally separate from normal skill-component semantics.
Ordinary skill damage/healing is crit-eligible by default; proc and set effects
have additional scaling/type exceptions and must opt into this policy.

Only verified rule families are hardcoded here. Unknown or merely flat/unscaled
proc mechanics remain unresolved rather than being guessed.
"""

from dataclasses import dataclass
from enum import Enum


class ProcScalingKind(str, Enum):
    """Scaling/mechanic families relevant to proc critical eligibility."""

    OFFENSIVE_STATS = "offensive_stats"
    MAX_HEALTH = "max_health"
    ESCALATING_MODIFIER = "escalating_modifier"
    FLAT_OR_UNRESOLVED = "flat_or_unresolved"


class ProcDamageKind(str, Enum):
    """Special damage families that can override ordinary crit behavior."""

    STANDARD = "standard"
    OBLIVION = "oblivion"


@dataclass(frozen=True)
class ProcCriticalEligibility:
    can_crit: bool | None
    reason: str


def resolve_proc_critical_eligibility(
    *,
    scaling_kind: ProcScalingKind,
    damage_kind: ProcDamageKind = ProcDamageKind.STANDARD,
) -> ProcCriticalEligibility:
    """Resolve proc/set crit eligibility without borrowing the normal-skill rule.

    Current verified policy boundary:
    - Oblivion damage cannot critically strike.
    - Max-Health-scaled proc effects cannot critically strike/heal.
    - escalating/additional-modifier proc mechanics cannot critically strike.
    - proc effects that scale from offensive stats are crit-eligible.
    - flat/unresolved proc scaling remains unknown until separately verified.

    This function does not decide whether one proc may trigger another proc.
    Trigger eligibility is a separate mechanic.
    """

    if damage_kind is ProcDamageKind.OBLIVION:
        return ProcCriticalEligibility(
            can_crit=False,
            reason="Oblivion damage is a non-critical special damage family",
        )

    if scaling_kind is ProcScalingKind.MAX_HEALTH:
        return ProcCriticalEligibility(
            can_crit=False,
            reason="Max-Health-scaled proc effects are not crit-eligible",
        )

    if scaling_kind is ProcScalingKind.ESCALATING_MODIFIER:
        return ProcCriticalEligibility(
            can_crit=False,
            reason="escalating/additional-modifier proc effects are not crit-eligible",
        )

    if scaling_kind is ProcScalingKind.OFFENSIVE_STATS:
        return ProcCriticalEligibility(
            can_crit=True,
            reason="offensive-stat-scaled proc effects are crit-eligible",
        )

    return ProcCriticalEligibility(
        can_crit=None,
        reason="proc scaling/crit eligibility is not yet verified",
    )
