from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillCoefficient:
    """
    One ESO skill damage/healing coefficient.

    For coefficient type 8, ESO uses the general
    Max Stat + Power scaling model:

        value = (a * max_stat) + (b * power) + c
    """

    coefficient_number: int
    type: str

    a: float
    b: float
    c: float

    r: float = 1.0
    avg: float | None = None


@dataclass(frozen=True)
class SkillCoefficientResult:
    """
    Result of evaluating one skill coefficient.
    """

    coefficient_number: int
    coefficient_type: str

    max_stat: float
    power: float

    a: float
    b: float
    c: float

    raw_value: float
    scaled_value: float


def evaluate_skill_coefficient(
    coefficient: SkillCoefficient,
    *,
    max_stat: float,
    power: float,
) -> SkillCoefficientResult:
    """
    Evaluate one ESO skill coefficient.

    Type 8 currently represents the standard ESO
    Max Stat + Power scaling model.

    Formula:

        raw = (A * MaxStat) + (B * Power) + C

        scaled = raw * R

    R is applied after the base coefficient expression.
    """

    if max_stat < 0:
        raise ValueError(
            "max_stat cannot be negative."
        )

    if power < 0:
        raise ValueError(
            "power cannot be negative."
        )

    if coefficient.type != "8":
        raise ValueError(
            "Unsupported skill coefficient type: "
            f"{coefficient.type!r}"
        )

    raw_value = (
        coefficient.a * max_stat
        + coefficient.b * power
        + coefficient.c
    )

    scaled_value = (
        raw_value * coefficient.r
    )

    return SkillCoefficientResult(
        coefficient_number=(
            coefficient.coefficient_number
        ),
        coefficient_type=coefficient.type,
        max_stat=max_stat,
        power=power,
        a=coefficient.a,
        b=coefficient.b,
        c=coefficient.c,
        raw_value=raw_value,
        scaled_value=scaled_value,
    )