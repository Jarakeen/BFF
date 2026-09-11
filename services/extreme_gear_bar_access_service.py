from __future__ import annotations

"""Resolve which weapon bars a proven Extreme gear state may activate.

Ordinary ESO builds may activate both front and back weapon sets. Oakensoul Ring
changes that legality: backup equipment may still exist on the character, but the
build is one-bar and cannot activate/swap to the backup bar. This service keeps
that rule separate from gear stat/count math.
"""

from dataclasses import dataclass

from services.extreme_dual_bar_gear_state_service import ExtremeDualBarGearState
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization


OAKENSOUL_RING = "Oakensoul Ring"


@dataclass(frozen=True)
class ExtremeGearBarAccess:
    activatable_bars: tuple[str, ...]
    can_swap: bool
    source_rule: str = ""
    unresolved: tuple[str, ...] = ()

    def allows(self, bar: str) -> bool:
        return str(bar or "").strip().casefold() in self.activatable_bars


class ExtremeGearBarAccessService:
    """Apply reviewed gear rules that mutate bar activation legality."""

    @staticmethod
    def _set_count(realization: ExtremeNamedGearSetRealization, set_name: str) -> int:
        target = str(set_name or "").strip().casefold()
        names = tuple(getattr(realization, "set_names", ()) or ())
        counts = tuple(getattr(realization, "counts", ()) or ())
        return sum(
            int(count)
            for name, count in zip(names, counts)
            if str(name or "").strip().casefold() == target
        )

    @classmethod
    def resolve(cls, state: ExtremeDualBarGearState) -> ExtremeGearBarAccess:
        front_oakensoul = cls._set_count(state.front, OAKENSOUL_RING)
        back_oakensoul = cls._set_count(state.back, OAKENSOUL_RING)

        if bool(front_oakensoul) != bool(back_oakensoul):
            return ExtremeGearBarAccess(
                activatable_bars=(),
                can_swap=False,
                unresolved=(
                    "Front/back Extreme gear state disagrees on shared Oakensoul Ring equipment",
                ),
            )

        if front_oakensoul > 0:
            return ExtremeGearBarAccess(
                activatable_bars=("front",),
                can_swap=False,
                source_rule="Oakensoul Ring: unable to swap between Primary and Backup Weapon Sets",
            )

        return ExtremeGearBarAccess(
            activatable_bars=("front", "back"),
            can_swap=True,
        )


__all__ = [
    "ExtremeGearBarAccess",
    "ExtremeGearBarAccessService",
    "OAKENSOUL_RING",
]
