from __future__ import annotations

from dataclasses import dataclass

from .resource_costs import ResourceType
from .restoration_events import ResourceRestorationEvent


RESTORATION_STAFF_ABSORB_MAGICKA = 600
RESTORATION_STAFF_ABSORB_COOLDOWN_SECONDS = 0.25
WARDEN_NATURES_GIFT_MAGICKA = 250
WARDEN_NATURES_GIFT_STAMINA = 250
WARDEN_NATURES_GIFT_COOLDOWN_SECONDS = 1.0


@dataclass(frozen=True)
class TriggeredRestorationSource:
    """Verified flat restoration source with an explicit trigger cooldown."""

    source: str
    cooldown_seconds: float
    events: tuple[tuple[ResourceType, int], ...]

    def __post_init__(self) -> None:
        if not str(self.source or "").strip():
            raise ValueError("Triggered restoration source requires a source")
        if self.cooldown_seconds < 0:
            raise ValueError("Triggered restoration cooldown cannot be negative")
        if not self.events:
            raise ValueError("Triggered restoration source requires at least one resource event")
        for resource, amount in self.events:
            if amount < 0:
                raise ValueError(
                    f"Triggered restoration amount cannot be negative: {resource.value}={amount}"
                )

    def create_events(self, *, time_seconds: float) -> tuple[ResourceRestorationEvent, ...]:
        return tuple(
            ResourceRestorationEvent(
                time_seconds=float(time_seconds),
                resource=resource,
                amount=amount,
                source=self.source,
            )
            for resource, amount in self.events
        )


RESTORATION_STAFF_ABSORB = TriggeredRestorationSource(
    source="Restoration Staff: Absorb",
    cooldown_seconds=RESTORATION_STAFF_ABSORB_COOLDOWN_SECONDS,
    events=((ResourceType.MAGICKA, RESTORATION_STAFF_ABSORB_MAGICKA),),
)

WARDEN_NATURES_GIFT = TriggeredRestorationSource(
    source="Warden: Nature's Gift",
    cooldown_seconds=WARDEN_NATURES_GIFT_COOLDOWN_SECONDS,
    events=(
        (ResourceType.MAGICKA, WARDEN_NATURES_GIFT_MAGICKA),
        (ResourceType.STAMINA, WARDEN_NATURES_GIFT_STAMINA),
    ),
)
