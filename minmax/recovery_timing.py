from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .conditional_recovery import TimedRecoveryModifier, additive_recovery_bonus_at
from .resource_costs import ResourceType
from .resource_state import StaticResourcePool


# Current in-combat ESO recovery cadence. Character-sheet recovery is restored
# once per recovery tick, not once per second.
IN_COMBAT_RECOVERY_INTERVAL_SECONDS = 2.0


@dataclass(frozen=True)
class RecoveryActivityState:
    """Ordinary activity flags that may suppress a primary resource recovery tick.

    This baseline intentionally models only the ordinary rules verified for
    current ESO behavior. Effects that replace or invert suppression rules
    (for example Stormweaver's Cavort) require their own explicit override
    rather than mutating this baseline silently.
    """

    blocking: bool = False
    sprinting: bool = False
    sneaking: bool = False

    def suppresses(self, resource: ResourceType) -> bool:
        if resource is ResourceType.STAMINA:
            return self.blocking or self.sprinting or self.sneaking
        return False


@dataclass(frozen=True)
class RecoveryTick:
    """One deterministic in-combat recovery event for a primary resource."""

    resource: ResourceType
    interval_seconds: float
    displayed_recovery: int
    additive_recovery_bonus: int
    effective_recovery: int
    suppressed: bool
    restored_amount: int


@dataclass(frozen=True)
class ScheduledRecoveryTick:
    """One recovery tick placed at an explicit time on a deterministic timeline."""

    time_seconds: float
    tick: RecoveryTick


@dataclass(frozen=True)
class AppliedRecoveryTick:
    """Result of applying one scheduled recovery tick to one resource pool."""

    time_seconds: float
    resource: ResourceType
    before: int
    attempted_restore: int
    applied_restore: int
    after: int
    maximum: int
    suppressed: bool


RecoveryActivityResolver = Callable[[float], RecoveryActivityState]


def resolve_in_combat_recovery_tick(
    pool: StaticResourcePool,
    activity: RecoveryActivityState = RecoveryActivityState(),
    *,
    additive_recovery_bonus: int = 0,
) -> RecoveryTick:
    """Resolve one ordinary in-combat ESO recovery tick.

    The character-sheet recovery value is the amount restored at the tick.
    Temporary additive recovery modifiers are added before ordinary suppression
    is evaluated. Ordinary in-combat recovery ticks occur every 2 seconds.
    Stamina recovery is suppressed when blocking, sprinting, or sneaking at the
    tick instant. Health and Magicka are not suppressed by those ordinary
    activity flags.

    Conditional effects that alter which resource is suppressed remain outside
    this baseline contract.
    """

    bonus = int(additive_recovery_bonus)
    if bonus < 0:
        raise ValueError(f"Additive recovery bonus cannot be negative: {bonus}")

    displayed = int(pool.displayed_recovery)
    effective = displayed + bonus
    suppressed = activity.suppresses(pool.resource)
    restored = 0 if suppressed else effective
    return RecoveryTick(
        resource=pool.resource,
        interval_seconds=IN_COMBAT_RECOVERY_INTERVAL_SECONDS,
        displayed_recovery=displayed,
        additive_recovery_bonus=bonus,
        effective_recovery=effective,
        suppressed=suppressed,
        restored_amount=restored,
    )


def schedule_in_combat_recovery_ticks(
    pool: StaticResourcePool,
    *,
    duration_seconds: float,
    first_tick_seconds: float = IN_COMBAT_RECOVERY_INTERVAL_SECONDS,
    activity_at: RecoveryActivityResolver | None = None,
    recovery_modifiers: tuple[TimedRecoveryModifier, ...] = (),
) -> tuple[ScheduledRecoveryTick, ...]:
    """Schedule ordinary recovery ticks within one deterministic time window.

    ``first_tick_seconds`` makes recovery phase explicit. A fresh baseline
    window therefore defaults to ticks at 2, 4, 6, ... seconds rather than
    inventing a tick at time zero. A later combat timeline may pass a different
    first-tick offset when it already knows the resource recovery phase.

    Activity and timed recovery modifiers are resolved independently at every
    tick instant. This matters because temporary effects may begin or expire
    between ticks, and Stamina suppression for one tick must not suppress every
    other tick in the window.
    """

    duration = float(duration_seconds)
    first_tick = float(first_tick_seconds)
    if duration < 0:
        raise ValueError(f"Recovery schedule duration cannot be negative: {duration_seconds}")
    if first_tick <= 0:
        raise ValueError(f"First recovery tick must be after time zero: {first_tick_seconds}")

    resolve_activity = activity_at or (lambda _time: RecoveryActivityState())
    scheduled: list[ScheduledRecoveryTick] = []
    tick_index = 0
    while True:
        time_seconds = first_tick + (tick_index * IN_COMBAT_RECOVERY_INTERVAL_SECONDS)
        if time_seconds > duration:
            break
        activity = resolve_activity(time_seconds)
        if not isinstance(activity, RecoveryActivityState):
            raise ValueError(
                "Recovery activity resolver must return RecoveryActivityState; "
                f"received {type(activity).__name__} at {time_seconds:g}s"
            )
        bonus = additive_recovery_bonus_at(
            recovery_modifiers,
            resource=pool.resource,
            time_seconds=time_seconds,
        )
        scheduled.append(
            ScheduledRecoveryTick(
                time_seconds=time_seconds,
                tick=resolve_in_combat_recovery_tick(
                    pool,
                    activity,
                    additive_recovery_bonus=bonus,
                ),
            )
        )
        tick_index += 1

    return tuple(scheduled)


def apply_scheduled_recovery_tick(
    pool: StaticResourcePool,
    current_amount: int,
    event: ScheduledRecoveryTick,
) -> AppliedRecoveryTick:
    """Apply one scheduled recovery tick and clamp the pool at its maximum.

    Recovery timing is responsible only for the recovery event itself. Costs,
    flat restores, heavy attacks, and external restores remain separate event
    types for the later sustain timeline.
    """

    current = int(current_amount)
    maximum = int(pool.maximum)
    if current < 0:
        raise ValueError(f"Current resource cannot be negative: {current_amount}")
    if current > maximum:
        raise ValueError(
            f"Current {pool.resource.value} exceeds pool maximum: {current} > {maximum}"
        )
    if event.tick.resource is not pool.resource:
        raise ValueError(
            "Recovery tick resource does not match pool: "
            f"{event.tick.resource.value} != {pool.resource.value}"
        )

    attempted = int(event.tick.restored_amount)
    after = min(maximum, current + attempted)
    applied = after - current
    return AppliedRecoveryTick(
        time_seconds=float(event.time_seconds),
        resource=pool.resource,
        before=current,
        attempted_restore=attempted,
        applied_restore=applied,
        after=after,
        maximum=maximum,
        suppressed=event.tick.suppressed,
    )
