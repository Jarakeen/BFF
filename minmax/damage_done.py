from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DamageDoneModifiers:
    """Additive ESO Damage Done categories for one attacker snapshot.

    Values are decimal ratios (0.05 == 5%). The event classifier decides which
    categories apply; applicable categories share one additive Damage Done
    bucket rather than multiplying independently.
    """

    generic: float = 0.0
    direct: float = 0.0
    dot: float = 0.0
    area: float = 0.0
    single_target: float = 0.0

    magic: float = 0.0
    physical: float = 0.0
    flame: float = 0.0
    frost: float = 0.0
    shock: float = 0.0
    poison: float = 0.0
    disease: float = 0.0
    bleed: float = 0.0

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if value < -1.0:
                raise ValueError(f"Damage Done modifier {name} cannot be below -100%")


@dataclass(frozen=True)
class DamageDoneBreakdown:
    generic: float = 0.0
    delivery: float = 0.0
    target_shape: float = 0.0
    damage_type: float = 0.0

    @property
    def total(self) -> float:
        return self.generic + self.delivery + self.target_shape + self.damage_type

    @property
    def multiplier(self) -> float:
        return max(0.0, 1.0 + self.total)


_TYPE_FIELDS = {
    # The DD profile calls the base magic family "magical" while the ESO math
    # source calls the modifier category Magic Damage Done. Accept both names.
    "magic": "magic",
    "magical": "magic",
    "physical": "physical",
    "flame": "flame",
    "frost": "frost",
    "shock": "shock",
    "poison": "poison",
    "disease": "disease",
    "bleed": "bleed",
}


def resolve_damage_done(
    modifiers: DamageDoneModifiers,
    *,
    damage_type: str | None,
    is_dot: bool = False,
    is_aoe: bool = False,
) -> DamageDoneBreakdown:
    """Resolve only the Damage Done categories applicable to one event."""

    delivery = modifiers.dot if is_dot else modifiers.direct
    target_shape = modifiers.area if is_aoe else modifiers.single_target

    type_key = str(damage_type or "").strip().casefold()
    field = _TYPE_FIELDS.get(type_key)
    typed = float(getattr(modifiers, field)) if field else 0.0

    return DamageDoneBreakdown(
        generic=float(modifiers.generic),
        delivery=float(delivery),
        target_shape=float(target_shape),
        damage_type=typed,
    )
