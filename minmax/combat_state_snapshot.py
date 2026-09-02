from __future__ import annotations
from dataclasses import dataclass
import math
from .combat_state import CombatState
from .runtime_effect_window import RuntimeEffectActiveWindow, partition_runtime_effect_windows

@dataclass(frozen=True)
class CombatantSnapshot:
    identity: str
    current_health: float | None = None
    maximum_health: float | None = None
    current_magicka: float | None = None
    maximum_magicka: float | None = None
    current_stamina: float | None = None
    maximum_stamina: float | None = None
    current_ultimate: float | None = None
    def __post_init__(self):
        if not self.identity.strip(): raise ValueError("combatant identity is required")
        for value in self.__dict__.values():
            if value is not None and not isinstance(value,str) and (not math.isfinite(value) or value < 0): raise ValueError("resources must be finite and non-negative")
    def health_fraction(self):
        return None if self.current_health is None or not self.maximum_health else self.current_health/self.maximum_health

@dataclass(frozen=True)
class CombatStateSnapshot:
    time_seconds: float
    player: CombatantSnapshot
    targets: tuple[CombatantSnapshot,...] = ()
    active_windows: tuple[RuntimeEffectActiveWindow,...] = ()
    combat_state: CombatState = CombatState()
    unresolved: tuple[str,...] = ()
    def __post_init__(self):
        if not math.isfinite(self.time_seconds) or self.time_seconds < 0: raise ValueError("time_seconds must be finite and non-negative")
        if len({t.identity for t in self.targets}) != len(self.targets): raise ValueError("target identities must be unique")
    @classmethod
    def from_windows(cls,time_seconds,player,windows,combat_state=CombatState(),targets=()):
        return cls(time_seconds,player,tuple(targets),partition_runtime_effect_windows(windows,at_time_seconds=time_seconds).active,combat_state)
    def target(self,identity):
        return next((t for t in self.targets if t.identity == identity),None)
    def meets_health_threshold(self,threshold,target=None):
        combatant=self.player if target is None else self.target(target)
        return None if combatant is None or combatant.health_fraction() is None else combatant.health_fraction() < threshold
