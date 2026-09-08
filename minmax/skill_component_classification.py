from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SkillEffectKind(str, Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    SHIELD = "shield"
    UTILITY = "utility"
    UNKNOWN = "unknown"


class HealRecipientScope(str, Enum):
    """Reviewed recipient class for one coefficient-bearing HEAL component."""

    SELF = "self"
    ALLY = "ally"
    SELF_OR_ALLY = "self_or_ally"
    GROUP = "group"
    PET = "pet"


class HealTemporalScope(str, Enum):
    """Reviewed time semantics for one coefficient-bearing HEAL component."""

    DIRECT = "direct"
    PERIODIC = "periodic"
    DELAYED = "delayed"
    CHANNEL_TICK = "channel_tick"


@dataclass(frozen=True)
class SkillComponentClassification:
    """Verified identity for one coefficient-bearing skill component.

    Classification is deliberately keyed below the whole-skill level because
    one ESO ability can contain multiple mechanically different components
    (for example an initial direct hit plus a DoT, or a direct self heal plus a
    later ally/periodic heal). Optional fields remain ``None`` when imported or
    reviewed evidence does not prove them.

    ``heal_recipient_key`` and ``heal_event_key`` are identity keys, not display
    labels. Components with the same proven recipient key and event key may be
    combined into one Actual Heal event. Different keys must remain separate.
    """

    skill_rank_id: int
    coefficient_number: int
    effect_kind: SkillEffectKind = SkillEffectKind.UNKNOWN
    damage_type: str | None = None
    is_dot: bool | None = None
    is_aoe: bool | None = None
    can_crit: bool | None = None
    source: str = ""
    confidence: float | None = None
    heal_recipient_scope: HealRecipientScope | None = None
    heal_temporal_scope: HealTemporalScope | None = None
    heal_recipient_key: str | None = None
    heal_event_key: str | None = None

    @property
    def is_damage(self) -> bool:
        return self.effect_kind is SkillEffectKind.DAMAGE

    @property
    def is_heal(self) -> bool:
        return self.effect_kind is SkillEffectKind.HEAL

    @property
    def is_complete_damage_identity(self) -> bool:
        return (
            self.is_damage
            and self.damage_type is not None
            and self.is_dot is not None
            and self.is_aoe is not None
            and self.can_crit is not None
        )

    @property
    def is_complete_heal_event_identity(self) -> bool:
        return (
            self.is_heal
            and self.heal_recipient_scope is not None
            and self.heal_temporal_scope is not None
            and bool(str(self.heal_recipient_key or "").strip())
            and bool(str(self.heal_event_key or "").strip())
            and self.can_crit is not None
        )
