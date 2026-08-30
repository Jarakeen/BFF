from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillCoefficient:
    """One canonical ESO skill coefficient component.

    The current Phase 3 foundation supports coefficient type 8, the standard
    Max Resource + Weapon/Spell Damage model already used by the project's
    earlier coefficient implementation. Other coefficient types remain
    explicit unresolved mechanics until their formulas are verified.

    ``r`` is retained exactly as supplied by the UESP coefficient export for
    provenance. In UESP's regression-derived coefficient data this value is a
    fit-quality statistic (R/R²-style regression metadata), not a game-side
    multiplier and therefore must not alter the evaluated skill value.
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

    @property
    def fit_quality(self) -> float:
        """Regression fit metadata carried from the UESP source export."""

        return self.r


@dataclass(frozen=True)
class SkillPowerEquivalentDiagnostic:
    """Power-only equivalent for an observed value.

    This is a diagnostic, not a claim about the actual ESO mechanic. It answers
    the counterfactual question: with the evaluated resource terms and constants
    held fixed, what offensive power would make the raw type-8 coefficient
    expression equal the observed value?
    """

    observed_value: float
    current_power: float
    equivalent_power: float
    power_delta: float
    raw_value_at_current_power: float
    observed_to_raw_ratio: float | None


@dataclass(frozen=True)
class InactiveSkillCoefficientTrace:
    """One source coefficient slot that is explicitly marked inactive."""

    coefficient_number: int
    coefficient_type: str
    a: float
    b: float
    c: float
    r: float
    reason: str


class UnsupportedSkillCoefficientType(ValueError):
    pass


def is_inactive_skill_coefficient(coefficient: SkillCoefficient) -> bool:
    """Recognize only UESP's exact empty coefficient-slot marker.

    Negative coefficients can be real formula terms, and two known type -1
    records contain passive data. Neither case may be silently discarded.
    """

    return (
        str(coefficient.type or "").strip() == "-1"
        and float(coefficient.a) == -1.0
        and float(coefficient.b) == -1.0
        and float(coefficient.c) == -1.0
        and float(coefficient.r) == -1.0
    )


def evaluate_skill_coefficient(
    coefficient: SkillCoefficient,
    *,
    max_stat: float,
    power: float,
) -> SkillCoefficientTrace:
    """Evaluate one raw ESO coefficient component without tooltip rounding.

    Verified type-8 relation::

        value = (A * MaxStat) + (B * Power) + C

    The source ``R`` value is regression-fit metadata. It is preserved on the
    returned trace for auditability but is deliberately *not* multiplied into
    the game value.

    Rounding and combat modifiers deliberately live above this layer. A raw
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
    final_value = before_r

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


def power_equivalent_for_observed_value(
    components: tuple[SkillCoefficientTrace, ...],
    observed_value: float,
) -> SkillPowerEquivalentDiagnostic | None:
    """Solve the type-8 expression for power as a diagnostic comparison.

    All components must have been evaluated with the same offensive-power input.
    A zero combined B coefficient cannot be solved for power and returns None.
    """

    if not components:
        return None

    powers = {float(component.power) for component in components}
    if len(powers) != 1:
        raise ValueError("coefficient components use different offensive-power inputs")

    combined_b = sum(float(component.b) for component in components)
    if combined_b == 0.0:
        return None

    fixed_terms = sum(
        float(component.resource_term) + float(component.constant_term)
        for component in components
    )
    current_power = next(iter(powers))
    raw_value = sum(float(component.final_value) for component in components)
    equivalent_power = (float(observed_value) - fixed_terms) / combined_b
    ratio = float(observed_value) / raw_value if raw_value != 0.0 else None

    return SkillPowerEquivalentDiagnostic(
        observed_value=float(observed_value),
        current_power=current_power,
        equivalent_power=equivalent_power,
        power_delta=equivalent_power - current_power,
        raw_value_at_current_power=raw_value,
        observed_to_raw_ratio=ratio,
    )
