from __future__ import annotations

from dataclasses import dataclass

from .resource_costs import ResourceType


ENLIVENING_OVERFLOW_MAX_BONUS = 150
ENLIVENING_OVERFLOW_MAX_MAGICKA_PERCENT = 0.005
ENLIVENING_OVERFLOW_DURATION_SECONDS = 6.0
ENLIVENING_OVERFLOW_TARGET_COOLDOWN_SECONDS = 12.0


@dataclass(frozen=True)
class TimedRecoveryModifier:
    """One temporary additive character-sheet recovery modifier.

    ``amount`` is added to the displayed recovery value for each affected
    resource while the modifier is active. Recovery timing remains owned by the
    Phase 4 recovery scheduler rather than this contract.
    """

    source: str
    amount: int
    resources: tuple[ResourceType, ...]
    starts_at_seconds: float
    duration_seconds: float
    cooldown_seconds: float | None = None

    def __post_init__(self) -> None:
        if not str(self.source or "").strip():
            raise ValueError("Timed recovery modifier requires a source")
        if self.amount < 0:
            raise ValueError(f"Recovery modifier amount cannot be negative: {self.amount}")
        if not self.resources:
            raise ValueError("Timed recovery modifier requires at least one resource")
        if self.starts_at_seconds < 0:
            raise ValueError("Timed recovery modifier start cannot be negative")
        if self.duration_seconds <= 0:
            raise ValueError("Timed recovery modifier duration must be positive")
        if self.cooldown_seconds is not None and self.cooldown_seconds < 0:
            raise ValueError("Timed recovery modifier cooldown cannot be negative")

    @property
    def ends_at_seconds(self) -> float:
        return self.starts_at_seconds + self.duration_seconds

    def active_at(self, time_seconds: float) -> bool:
        time = float(time_seconds)
        return self.starts_at_seconds <= time < self.ends_at_seconds

    def applies_to(self, resource: ResourceType, *, time_seconds: float) -> bool:
        return resource in self.resources and self.active_at(time_seconds)


def enlivening_overflow_recovery_bonus(max_magicka: int) -> int:
    """Return Enlivening Overflow's current capped additive recovery bonus."""

    maximum = int(max_magicka)
    if maximum < 0:
        raise ValueError(f"Max Magicka cannot be negative: {max_magicka}")
    raw = maximum * ENLIVENING_OVERFLOW_MAX_MAGICKA_PERCENT
    return min(ENLIVENING_OVERFLOW_MAX_BONUS, int(raw))


def create_enlivening_overflow_modifier(
    *,
    max_magicka: int,
    triggered_at_seconds: float,
) -> TimedRecoveryModifier:
    """Create one Enlivening Overflow buff window after a qualifying overheal."""

    return TimedRecoveryModifier(
        source="Champion Points: Enlivening Overflow",
        amount=enlivening_overflow_recovery_bonus(max_magicka),
        resources=(ResourceType.HEALTH, ResourceType.MAGICKA, ResourceType.STAMINA),
        starts_at_seconds=float(triggered_at_seconds),
        duration_seconds=ENLIVENING_OVERFLOW_DURATION_SECONDS,
        cooldown_seconds=ENLIVENING_OVERFLOW_TARGET_COOLDOWN_SECONDS,
    )


def additive_recovery_bonus_at(
    modifiers: tuple[TimedRecoveryModifier, ...],
    *,
    resource: ResourceType,
    time_seconds: float,
) -> int:
    """Sum additive recovery modifiers active for one resource at one instant."""

    return sum(
        modifier.amount
        for modifier in modifiers
        if modifier.applies_to(resource, time_seconds=time_seconds)
    )
