from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


@dataclass(frozen=True)
class CostFormulaCandidate:
    name: str
    raw_value: float
    floor: int
    nearest_half_up: int
    ceiling: int


def _roundings(value: float) -> tuple[int, int, int]:
    decimal = Decimal(str(value))
    return (
        int(decimal.to_integral_value(rounding=ROUND_FLOOR)),
        int(decimal.to_integral_value(rounding=ROUND_HALF_UP)),
        int(decimal.to_integral_value(rounding=ROUND_CEILING)),
    )


def _candidate(name: str, value: float) -> CostFormulaCandidate:
    floor, nearest, ceiling = _roundings(value)
    return CostFormulaCandidate(
        name=name,
        raw_value=value,
        floor=floor,
        nearest_half_up=nearest,
        ceiling=ceiling,
    )


def evaluate_cost_formula_candidates(
    *,
    base_cost: float,
    flat_reduction: float = 0.0,
    percent_reduction: float = 0.0,
    percent_increase: float = 0.0,
) -> tuple[CostFormulaCandidate, ...]:
    """Evaluate plausible ESO action-cost ordering candidates.

    This is a validation aid, not canonical combat math. Phase 4 keeps these
    alternatives explicit until current in-game observations distinguish the
    real ordering and rounding rule.
    """

    base = float(base_cost)
    flat = float(flat_reduction)
    reduction = float(percent_reduction)
    increase = float(percent_increase)

    if base < 0 or flat < 0:
        raise ValueError("Base cost and flat reduction cannot be negative")
    if not 0.0 <= reduction <= 1.0:
        raise ValueError("Percent reduction must be a decimal ratio from 0 to 1")
    if increase < 0.0:
        raise ValueError("Percent increase cannot be negative")

    # Candidate A: flat reduction first, then summed percentage reduction,
    # then percentage increase.
    flat_then_percent = max(0.0, base - flat) * (1.0 - reduction) * (1.0 + increase)

    # Candidate B: percentage reduction first, then flat reduction, then
    # percentage increase.
    percent_then_flat = max(0.0, base * (1.0 - reduction) - flat) * (1.0 + increase)

    # Candidate C: percentage increase applies to the base before reductions.
    increase_then_flat_percent = max(0.0, base * (1.0 + increase) - flat) * (1.0 - reduction)

    return (
        _candidate("flat_then_percent_then_increase", flat_then_percent),
        _candidate("percent_then_flat_then_increase", percent_then_flat),
        _candidate("increase_then_flat_then_percent", increase_then_flat_percent),
    )


def matching_candidates(
    candidates: tuple[CostFormulaCandidate, ...],
    observed_cost: int,
) -> tuple[tuple[str, str], ...]:
    """Return candidate/rounding pairs that exactly match an observed cost."""

    observed = int(observed_cost)
    matches: list[tuple[str, str]] = []
    for candidate in candidates:
        for rounding_name, value in (
            ("floor", candidate.floor),
            ("nearest_half_up", candidate.nearest_half_up),
            ("ceiling", candidate.ceiling),
        ):
            if value == observed:
                matches.append((candidate.name, rounding_name))
    return tuple(matches)
