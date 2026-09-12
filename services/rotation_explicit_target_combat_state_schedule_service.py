from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.combat_state import CombatState


@dataclass(frozen=True)
class RotationTargetCombatStateWindow:
    """One explicit half-open target-state window [start, end)."""

    start_seconds: float
    end_seconds: float
    active_buffs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        start = float(self.start_seconds)
        end = float(self.end_seconds)
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError("target combat-state window bounds must be finite")
        if start < 0.0:
            raise ValueError("target combat-state window start cannot be negative")
        if end <= start:
            raise ValueError("target combat-state window end must be greater than start")
        object.__setattr__(self, "start_seconds", start)
        object.__setattr__(self, "end_seconds", end)
        object.__setattr__(
            self,
            "active_buffs",
            tuple(
                dict.fromkeys(
                    " ".join(str(value or "").strip().split())
                    for value in self.active_buffs
                    if str(value or "").strip()
                )
            ),
        )

    def contains(self, time_seconds: float) -> bool:
        value = float(time_seconds)
        return self.start_seconds <= value < self.end_seconds


class RotationExplicitTargetCombatStateScheduleService:
    """Resolve authoritative target CombatState from caller-supplied windows.

    This service deliberately does not infer activations from gear, skills, status
    chance, or encounter folklore. If the caller chooses this service, time outside
    every configured window is authoritative known state with no scheduled buffs.
    Overlapping windows union their named buffs. Sequence does not alter membership;
    it remains accepted for compatibility with the shared runtime resolver contract.
    """

    def __init__(
        self,
        windows: tuple[RotationTargetCombatStateWindow, ...] = (),
        *,
        in_combat: bool = True,
    ) -> None:
        self.windows = tuple(
            sorted(
                windows,
                key=lambda item: (
                    item.start_seconds,
                    item.end_seconds,
                    tuple(name.casefold() for name in item.active_buffs),
                ),
            )
        )
        self.in_combat = bool(in_combat)

    def resolve(
        self,
        time_seconds: float,
        sequence: int | None = None,
    ) -> CombatState:
        del sequence
        value = float(time_seconds)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("target combat-state time must be finite and non-negative")

        buffs: list[str] = []
        for window in self.windows:
            if window.contains(value):
                buffs.extend(window.active_buffs)
        return CombatState(
            in_combat=self.in_combat,
            active_buffs=tuple(dict.fromkeys(buffs)),
        )

    def __call__(
        self,
        time_seconds: float,
        sequence: int | None = None,
    ) -> CombatState:
        return self.resolve(time_seconds, sequence)


__all__ = [
    "RotationExplicitTargetCombatStateScheduleService",
    "RotationTargetCombatStateWindow",
]
