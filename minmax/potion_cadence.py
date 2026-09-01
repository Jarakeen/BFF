from __future__ import annotations

"""Explicit potion cooldown and Medicinal Use cadence semantics.

This layer deliberately does not infer whether a character owns Medicinal Use.
Callers provide the passive rank explicitly. The base potion cooldown is modeled
separately from effect duration so later cooldown-reduction mechanics can be
added without rewriting potion-use evidence.
"""

from dataclasses import dataclass

from .potion_active_window import PotionActiveWindow
from .potion_use_event import PotionBuffGrant, PotionUseEvent

BASE_POTION_COOLDOWN_SECONDS = 45.0
_MEDICINAL_USE_BONUS_BY_RANK = {
    0: 0.0,
    1: 0.10,
    2: 0.20,
    3: 0.30,
}
_SECONDS_PRECISION = 9


def _seconds(value: float) -> float:
    """Normalize human-facing second arithmetic across binary-float noise."""
    return round(float(value), _SECONDS_PRECISION)


def medicinal_use_duration_multiplier(rank: int) -> float:
    try:
        normalized = int(rank)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Medicinal Use rank: {rank!r}") from exc
    if normalized not in _MEDICINAL_USE_BONUS_BY_RANK:
        raise ValueError("Medicinal Use rank must be between 0 and 3")
    return 1.0 + _MEDICINAL_USE_BONUS_BY_RANK[normalized]


@dataclass(frozen=True)
class PotionCadence:
    event: PotionUseEvent
    medicinal_use_rank: int = 0
    cooldown_seconds: float = BASE_POTION_COOLDOWN_SECONDS

    def __post_init__(self) -> None:
        rank = int(self.medicinal_use_rank)
        medicinal_use_duration_multiplier(rank)
        cooldown = _seconds(self.cooldown_seconds)
        if cooldown <= 0.0:
            raise ValueError("Potion cooldown must be positive")
        object.__setattr__(self, "medicinal_use_rank", rank)
        object.__setattr__(self, "cooldown_seconds", cooldown)

    @property
    def duration_multiplier(self) -> float:
        return medicinal_use_duration_multiplier(self.medicinal_use_rank)

    def effective_duration(self, grant: PotionBuffGrant) -> float:
        return _seconds(float(grant.duration) * self.duration_multiplier)

    def window(self, elapsed_seconds: float) -> PotionActiveWindow:
        return PotionActiveWindow(
            self.event,
            elapsed_seconds=elapsed_seconds,
            duration_multiplier=self.duration_multiplier,
        )

    @property
    def minimum_buff_duration(self) -> float | None:
        if not self.event.buff_grants:
            return None
        return min(self.effective_duration(grant) for grant in self.event.buff_grants)

    @property
    def maximum_buff_duration(self) -> float | None:
        if not self.event.buff_grants:
            return None
        return max(self.effective_duration(grant) for grant in self.event.buff_grants)

    @property
    def guaranteed_overlap_seconds(self) -> float | None:
        duration = self.minimum_buff_duration
        if duration is None:
            return None
        return _seconds(max(0.0, duration - self.cooldown_seconds))

    @property
    def guaranteed_gap_seconds(self) -> float | None:
        duration = self.minimum_buff_duration
        if duration is None:
            return None
        return _seconds(max(0.0, self.cooldown_seconds - duration))

    def can_refresh_before_all_buffs_expire(self) -> bool:
        duration = self.minimum_buff_duration
        return bool(duration is not None and duration >= self.cooldown_seconds)
