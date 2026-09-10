from __future__ import annotations

"""Canonical component-layer Healing Received modifiers from combat state.

Healing Received is an event/recipient modifier, not a standing character-sheet
stat in the current BFF model. Resolve named Vitality/Defile effects here so
healing-event consumers share one deterministic interpretation.
"""

from dataclasses import dataclass

from .combat_state import CombatState


U50_HEALING_RECEIVED_RATIO_POINTS: dict[str, float] = {
    "Minor Vitality": 0.06,
    "Major Vitality": 0.12,
    "Minor Defile": -0.06,
    "Major Defile": -0.12,
}


@dataclass(frozen=True)
class HealingReceivedCombatStateResult:
    ratio_points: float
    sources: tuple[str, ...]

    @property
    def multiplier(self) -> float:
        return 1.0 + self.ratio_points


def resolve_healing_received_combat_state(
    combat_state: CombatState,
) -> HealingReceivedCombatStateResult:
    """Return additive Healing Received ratio points for explicit named effects.

    U50 is the current live default. The named effects remain separately present
    in ``CombatState`` so future update-specific semantics can be versioned without
    changing the event-layer contract.
    """

    points = 0.0
    sources: list[str] = []
    for name in combat_state.active_buffs:
        value = U50_HEALING_RECEIVED_RATIO_POINTS.get(name)
        if value is None:
            continue
        points += float(value)
        sources.append(name)
    return HealingReceivedCombatStateResult(
        ratio_points=points,
        sources=tuple(sources),
    )
