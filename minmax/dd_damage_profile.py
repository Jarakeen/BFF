from dataclasses import dataclass


@dataclass(frozen=True)
class DDDamageProfile:
    """Rules describing which offensive stats a damage type uses."""

    damage_type: str
    offensive_stat: str
    penetration_stat: str


PHYSICAL_DAMAGE_TYPES = frozenset(
    {
        "physical",
        "poison",
        "disease",
        "bleed",
    }
)

MAGICAL_DAMAGE_TYPES = frozenset(
    {
        "magical",
        "flame",
        "frost",
        "shock",
    }
)


def get_dd_damage_profile(
    damage_type: str,
) -> DDDamageProfile:
    """Return the offensive-stat profile for a damage type."""

    normalized = damage_type.strip().lower()

    if normalized in PHYSICAL_DAMAGE_TYPES:
        return DDDamageProfile(
            damage_type=normalized,
            offensive_stat="weapon_damage",
            penetration_stat="physical_penetration",
        )

    if normalized in MAGICAL_DAMAGE_TYPES:
        return DDDamageProfile(
            damage_type=normalized,
            offensive_stat="spell_damage",
            penetration_stat="spell_penetration",
        )

    raise ValueError(
        f"Unsupported DD damage type: {damage_type!r}"
    )