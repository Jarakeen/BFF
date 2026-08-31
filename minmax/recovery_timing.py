from __future__ import annotations

from dataclasses import dataclass

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
    suppressed: bool
    restored_amount: int


def resolve_in_combat_recovery_tick(
    pool: StaticResourcePool,
    activity: RecoveryActivityState = RecoveryActivityState(),
) -> RecoveryTick:
    """Resolve one ordinary in-combat ESO recovery tick.

    The character-sheet recovery value is the amount restored at the tick.
    Ordinary in-combat recovery ticks occur every 2 seconds. Stamina recovery
    is suppressed when blocking, sprinting, or sneaking at the tick instant.
    Health and Magicka are not suppressed by those ordinary activity flags.

    Conditional effects that alter the resource affected by suppression are
    deliberately outside this baseline contract.
    """

    suppressed = activity.suppresses(pool.resource)
    restored = 0 if suppressed else int(pool.displayed_recovery)
    return RecoveryTick(
        resource=pool.resource,
        interval_seconds=IN_COMBAT_RECOVERY_INTERVAL_SECONDS,
        displayed_recovery=int(pool.displayed_recovery),
        suppressed=suppressed,
        restored_amount=restored,
    )
