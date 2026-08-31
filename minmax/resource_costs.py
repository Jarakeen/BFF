from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResourceType(str, Enum):
    """Canonical resource pools that an ESO action can consume."""

    MAGICKA = "magicka"
    STAMINA = "stamina"
    ULTIMATE = "ultimate"
    HEALTH = "health"


# ESO combat-mechanic flags used by ability.base_mechanic.
# Compound mechanics are represented by bitwise combinations of these values.
_RESOURCE_MECHANIC_BITS: tuple[tuple[int, ResourceType], ...] = (
    (1, ResourceType.MAGICKA),
    (4, ResourceType.STAMINA),
    (8, ResourceType.ULTIMATE),
    (32, ResourceType.HEALTH),
)
_KNOWN_RESOURCE_MECHANIC_MASK = sum(bit for bit, _ in _RESOURCE_MECHANIC_BITS)


def decode_resource_mechanic(base_mechanic: int) -> tuple[ResourceType, ...]:
    """Decode an ESO ability resource-mechanic bitmask.

    Examples:
        1  -> (MAGICKA,)
        4  -> (STAMINA,)
        5  -> (MAGICKA, STAMINA)
        36 -> (STAMINA, HEALTH)

    Unknown bits are rejected rather than guessed. A positive action cost with
    mechanic 0 is likewise unresolved and should not silently become a generic
    resource cost.
    """

    mechanic = int(base_mechanic)
    if mechanic <= 0:
        raise ValueError(f"Unsupported resource mechanic: {base_mechanic!r}")

    unknown_bits = mechanic & ~_KNOWN_RESOURCE_MECHANIC_MASK
    if unknown_bits:
        raise ValueError(
            f"Unsupported resource mechanic bits: mechanic={mechanic}, "
            f"unknown_bits={unknown_bits}"
        )

    resources = tuple(
        resource
        for bit, resource in _RESOURCE_MECHANIC_BITS
        if mechanic & bit
    )
    if not resources:
        raise ValueError(f"Unsupported resource mechanic: {base_mechanic!r}")
    return resources


@dataclass(frozen=True)
class BaseActionCost:
    """Unmodified resource cost resolved directly from one ability row.

    Timing and cost modifiers deliberately do not belong here. Phase 4 treats
    those as separate contracts so recurring/toggle behavior cannot be inferred
    from misleading raw fields such as cost_time or mechanic_time.
    """

    amount: float
    resources: tuple[ResourceType, ...]
    ability_id: int
    rank: int | None
    morph: int | None
    base_mechanic: int

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError(f"Action cost cannot be negative: {self.amount}")
        if not self.resources:
            raise ValueError("Action cost must consume at least one resource")


def resolve_base_action_cost(
    *,
    ability_id: int,
    base_cost: float,
    base_mechanic: int,
    rank: int | None = None,
    morph: int | None = None,
) -> BaseActionCost:
    """Create the canonical unmodified action-cost contract for an ability."""

    amount = float(base_cost)
    if amount <= 0:
        raise ValueError(
            f"Ability {ability_id} does not have a positive base cost: {base_cost!r}"
        )

    resources = decode_resource_mechanic(base_mechanic)
    return BaseActionCost(
        amount=amount,
        resources=resources,
        ability_id=int(ability_id),
        rank=None if rank is None else int(rank),
        morph=None if morph is None else int(morph),
        base_mechanic=int(base_mechanic),
    )
