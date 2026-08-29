from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillCoefficient:
    """One canonical ESO skill coefficient component.

    The current Phase 3 foundation supports coefficient type 8, the standard
    Max Resource + Weapon/Spell Damage model already used by the project's
    earlier coefficient implementation. Other coefficient types remain
    explicit unresolved mechanics until their formulas are verified.
    """

    coefficient_number: int
    type: str
    a: float
    b: float
    c: float
    r: float = 1.0
    avg: float | None = None


@dataclass(frozen=True)
class SkillScalingInputs:
    max_health: float
    max_magicka: float
    max_stamina: float
    weapon_damage: float
    spell_damage: float

    @property
    def highest_max_resource(self) -> float:
        return max(self.max_magicka, self.max_stamina)

    @property
    def highest_offensive_power(self) -> float:
        return max(self.weapon_damage, self.spell_damage)


@dataclass(frozen=True)
class SkillCoefficientTrace:
    coefficient_number: int
    coefficient_type: str
    max_stat: float
    power: float
    a: float
    b: float
    c: float
    r: float
    resource_term: float
    power_term: float
    constant_term: float
    before_r: float
    final_value: float


class UnsupportedSkillCoefficientType(ValueError):
    pass


def evaluate_skill_coefficient(
    coefficient: SkillCoefficient,
    *,
    max_stat: float,
    power: float,
) -> SkillCoefficientTrace:
    """Evaluate one raw ESO coefficient component without tooltip rounding.

    Type 8 uses the project's previously tested relation::

        before_r = (A * MaxStat) + (B * Power) + C
        value = before_r * R

    Rounding and combat multipliers deliberately live above this layer. A raw
    coefficient trace should remain useful when those later rules change.
    """

    coefficient_type = str(coefficient.type or "").strip()
    if coefficient_type != "8":
        raise UnsupportedSkillCoefficientType(
            f"Unsupported skill coefficient type: {coefficient_type!r}"
        )
    if max_stat < 0:
        raise ValueError("max_stat cannot be negative")
    if power < 0:
        raise ValueError("power cannot be negative")

    resource_term = float(coefficient.a) * float(max_stat)
    power_term = float(coefficient.b) * float(power)
    constant_term = float(coefficient.c)
    before_r = resource_term + power_term + constant_term
    final_value = before_r * float(coefficient.r)

    return SkillCoefficientTrace(
        coefficient_number=int(coefficient.coefficient_number),
        coefficient_type=coefficient_type,
        max_stat=float(max_stat),
        power=float(power),
        a=float(coefficient.a),
        b=float(coefficient.b),
        c=float(coefficient.c),
        r=float(coefficient.r),
        resource_term=resource_term,
        power_term=power_term,
        constant_term=constant_term,
        before_r=before_r,
        final_value=final_value,
    )
