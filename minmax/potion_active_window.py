from __future__ import annotations

"""Explicit active-window projection for one resolved potion-use event.

A potion-use event records what happens when a consumable is used. This module
answers the narrower temporal question: which named buffs from that event are
still active after a caller-supplied elapsed time?

Nothing here assumes automatic use, cooldown cadence, Medicinal Use, or standing
uptime. Callers must supply the elapsed time deliberately.
"""

from dataclasses import dataclass

from .combat_state import CombatState
from .potion_use_event import PotionBuffGrant, PotionUseEvent


@dataclass(frozen=True)
class PotionActiveWindow:
    event: PotionUseEvent
    elapsed_seconds: float = 0.0

    def __post_init__(self) -> None:
        elapsed = float(self.elapsed_seconds)
        if elapsed < 0.0:
            raise ValueError("PotionActiveWindow.elapsed_seconds cannot be negative")
        object.__setattr__(self, "elapsed_seconds", elapsed)

    @property
    def active_buff_grants(self) -> tuple[PotionBuffGrant, ...]:
        """Return grants whose ordinary sourced duration has not expired."""

        return tuple(
            grant
            for grant in self.event.buff_grants
            if self.elapsed_seconds < float(grant.duration)
        )

    @property
    def active_buff_names(self) -> tuple[str, ...]:
        seen: set[str] = set()
        names: list[str] = []
        for grant in self.active_buff_grants:
            key = grant.buff_name.casefold()
            if key in seen:
                continue
            seen.add(key)
            names.append(grant.buff_name)
        return tuple(names)

    def to_combat_state(self, base_state: CombatState | None = None) -> CombatState:
        """Merge only currently active potion buffs into an explicit snapshot."""

        base = base_state or CombatState()
        return CombatState(
            in_combat=base.in_combat,
            active_buffs=(*base.active_buffs, *self.active_buff_names),
            game_update=base.game_update,
        )
