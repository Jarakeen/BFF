from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class WeaponTraitEffectivenessResolution:
    multiplier: float
    evidence: tuple[str, ...] = ()


class WeaponTraitEffectivenessResolver:
    """Resolve reviewed global modifiers to active-bar Weapon Trait effectiveness.

    This is intentionally separate from individual trait arithmetic. Consumers
    continue to own Nirnhoned, Precise, Sharpened, Powered, Defending, and other
    trait formulas; this resolver owns only effects that scale the effectiveness
    of those trait formulas as a whole.

    Heartland Conqueror is the first reviewed source. Its five-piece bonus doubles
    Weapon Trait effectiveness (increase by 100%) while the five-piece condition is
    active on the current bar.
    """

    HEARTLAND_CONQUEROR = "Heartland Conqueror"
    HEARTLAND_REQUIRED_PIECES = 5
    HEARTLAND_MULTIPLIER = 2.0

    @classmethod
    def resolve(
        cls,
        set_counts: Mapping[str, int] | tuple[tuple[str, int], ...],
    ) -> WeaponTraitEffectivenessResolution:
        counts = dict(set_counts)
        heartland_count = max(
            (
                int(count)
                for name, count in counts.items()
                if str(name or "").strip().casefold()
                == cls.HEARTLAND_CONQUEROR.casefold()
            ),
            default=0,
        )
        if heartland_count < cls.HEARTLAND_REQUIRED_PIECES:
            return WeaponTraitEffectivenessResolution(multiplier=1.0)

        return WeaponTraitEffectivenessResolution(
            multiplier=cls.HEARTLAND_MULTIPLIER,
            evidence=(
                "Heartland Conqueror 5pc: Weapon Trait effectiveness increased by 100%",
            ),
        )


__all__ = [
    "WeaponTraitEffectivenessResolution",
    "WeaponTraitEffectivenessResolver",
]
