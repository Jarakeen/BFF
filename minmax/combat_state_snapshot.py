from __future__ import annotations
from dataclasses import dataclass
from .combat_state import CombatState
from .runtime_effect_window import RuntimeEffectActiveWindow, partition_runtime_effect_windows

@dataclass(frozen=True)
class CombatantSnapshot:
    identity: str
    current_health: float | None = None
    maximum_health: float | None = None
    def health_fraction(self) -> float | None:
        if self.current_health is None or self.maximum_health is None or self.maximum_health <= 0: return None
        return self.current_health / self.maximum_health

@dataclass(frozen=True)
class CombatStateSnapshot:
    time_seconds: float
    player: CombatantSnapshot
    active_windows: tuple[RuntimeEffectActiveWindow, ...] = ()
    combat_state: CombatState = CombatState()
    unresolved: tuple[str, ...] = ()
    @classmethod
    def from_windows(cls, time_seconds, player, windows, combat_state=CombatState()):
        active=partition_runtime_effect_windows(windows, at_time_seconds=time_seconds).active
        return cls(time_seconds, player, active, combat_state)
    def meets_health_threshold(self, threshold: float) -> bool | None:
        fraction=self.player.health_fraction()
        return None if fraction is None else fraction < threshold
