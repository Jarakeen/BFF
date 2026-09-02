from __future__ import annotations
from dataclasses import dataclass
import math
from .character_build.effect_instance import EffectVariant
from .combat_state import CombatState
from .runtime_effect_window import RuntimeEffectActiveWindow, partition_runtime_effect_windows
from .support_effect_category import SupportEffectCategory
@dataclass(frozen=True)
class CombatantSnapshot:
 identity:str; current_health:float|None=None; maximum_health:float|None=None; current_magicka:float|None=None; maximum_magicka:float|None=None; current_stamina:float|None=None; maximum_stamina:float|None=None; current_ultimate:float|None=None
 def __post_init__(s):
  if not s.identity.strip(): raise ValueError("combatant identity is required")
  if any(v is not None and (not math.isfinite(v) or v<0) for k,v in s.__dict__.items() if k!="identity"): raise ValueError("resources must be finite and non-negative")
 def health_fraction(s): return None if s.current_health is None or not s.maximum_health else s.current_health/s.maximum_health
@dataclass(frozen=True)
class ActiveEffectProjection:
 name:str; source:str; target:str|None; category:SupportEffectCategory|None; magnitude:float|None
@dataclass(frozen=True)
class CombatStateSnapshot:
 time_seconds:float; player:CombatantSnapshot; targets:tuple[CombatantSnapshot,...]=(); active_windows:tuple[RuntimeEffectActiveWindow,...]=(); combat_state:CombatState=CombatState(); unresolved:tuple[str,...]=(); active_effects:tuple[ActiveEffectProjection,...]=()
 def __post_init__(s):
  if not math.isfinite(s.time_seconds) or s.time_seconds<0: raise ValueError("time_seconds must be finite and non-negative")
  if len({t.identity for t in s.targets})!=len(s.targets): raise ValueError("target identities must be unique")
 @classmethod
 def from_windows(cls,time_seconds,player,windows,combat_state=CombatState(),targets=(),effects=()):
  active=partition_runtime_effect_windows(windows,at_time_seconds=time_seconds).active; by={e.name:e for e in effects}; unresolved=[]; projected=[]
  for w in active:
   e=by.get(w.effect_name)
   if e is None: unresolved.append("effect_metadata_required:"+w.effect_name); continue
   projected.append(ActiveEffectProjection(e.name,w.source,w.target,e.category,w.magnitude))
  return cls(time_seconds,player,tuple(targets),active,combat_state,tuple(dict.fromkeys(unresolved)),tuple(projected))
 def target(s,identity): return next((t for t in s.targets if t.identity==identity),None)
 def meets_health_threshold(s,threshold,target=None):
  c=s.player if target is None else s.target(target); return None if c is None or c.health_fraction() is None else c.health_fraction()<threshold
 def active_statuses(s,target):
  return tuple(e for e in s.active_effects if e.category is SupportEffectCategory.STATUS and e.target==target)
