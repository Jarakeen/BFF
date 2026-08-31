from __future__ import annotations

from dataclasses import dataclass

from .base_character_state import BaseCharacterState
from .resource_costs import ResourceType


@dataclass(frozen=True)
class StaticResourcePool:
    """Static character-sheet values for one primary ESO resource.

    ``displayed_recovery`` is intentionally named after the character-sheet
    value. Phase 4 has not yet established the authoritative recovery tick
    interval or suppression rules, so this value must not be treated as a
    per-second gain.
    """

    resource: ResourceType
    maximum: int
    displayed_recovery: int

    def __post_init__(self) -> None:
        if self.resource is ResourceType.ULTIMATE:
            raise ValueError("Ultimate is not a primary static resource pool")
        if self.maximum < 0:
            raise ValueError(f"Resource maximum cannot be negative: {self.maximum}")
        if self.displayed_recovery < 0:
            raise ValueError(
                f"Displayed resource recovery cannot be negative: {self.displayed_recovery}"
            )


@dataclass(frozen=True)
class StaticResourceState:
    """Phase 4 static resource foundation derived from BaseCharacterState.

    This is an adapter over the already-audited Phase 2 character-sheet
    calculation. It does not recalculate resources and does not infer temporal
    behavior such as recovery ticks, suppression, restoration events, or costs.
    """

    health: StaticResourcePool
    magicka: StaticResourcePool
    stamina: StaticResourcePool

    @classmethod
    def from_base_character_state(cls, state: BaseCharacterState) -> "StaticResourceState":
        return cls(
            health=StaticResourcePool(
                resource=ResourceType.HEALTH,
                maximum=int(state.max_health),
                displayed_recovery=int(state.health_recovery),
            ),
            magicka=StaticResourcePool(
                resource=ResourceType.MAGICKA,
                maximum=int(state.max_magicka),
                displayed_recovery=int(state.magicka_recovery),
            ),
            stamina=StaticResourcePool(
                resource=ResourceType.STAMINA,
                maximum=int(state.max_stamina),
                displayed_recovery=int(state.stamina_recovery),
            ),
        )

    def pool(self, resource: ResourceType) -> StaticResourcePool:
        if resource is ResourceType.HEALTH:
            return self.health
        if resource is ResourceType.MAGICKA:
            return self.magicka
        if resource is ResourceType.STAMINA:
            return self.stamina
        raise ValueError(f"No static primary resource pool for {resource.value}")
