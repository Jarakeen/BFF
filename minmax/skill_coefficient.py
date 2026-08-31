from __future__ import annotations

from dataclasses import dataclass

from .skill_coefficients import (
    SkillCoefficient,
    UnsupportedSkillCoefficientType,
    evaluate_skill_coefficient as evaluate_verified_skill_coefficient,
)


@dataclass(frozen=True)
class SkillCoefficientResult:
    """Compatibility result for one evaluated skill coefficient.

    ``raw_value`` and ``scaled_value`` are intentionally identical for the
    verified type-8 model. The UESP ``r`` field is regression-fit metadata,
    not a game-side multiplier. This result shape is retained for existing
    callers while the authoritative formula lives in ``skill_coefficients``.
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
    """Evaluate one coefficient using the verified Phase 3 implementation.

    Type 8::

        value = (A * MaxStat) + (B * Power) + C

    ``R`` is preserved on the source coefficient as regression metadata and is
    deliberately not multiplied into the result. Unsupported coefficient types
    remain explicit rather than being guessed.
    """

    try:
        trace = evaluate_verified_skill_coefficient(
            coefficient,
            max_stat=max_stat,
            power=power,
        )
    except UnsupportedSkillCoefficientType as exc:
        # Preserve the legacy public exception family (ValueError) while using
        # the canonical evaluator as the sole formula implementation.
        raise ValueError(str(exc)) from exc

    return SkillCoefficientResult(
        coefficient_number=trace.coefficient_number,
        coefficient_type=trace.coefficient_type,
        max_stat=trace.max_stat,
        power=trace.power,
        a=trace.a,
        b=trace.b,
        c=trace.c,
        raw_value=trace.final_value,
        scaled_value=trace.final_value,
    )
