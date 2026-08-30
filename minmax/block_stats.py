from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil

from .derived_stats import DerivedStatTrace
from .stat_ids import StatId


@dataclass(frozen=True)
class BlockCostModifier:
    label: str
    percent: float


@dataclass(frozen=True)
class BlockCostInputs:
    flat_reductions: tuple[tuple[str, float], ...] = ()
    sequential_modifiers: tuple[BlockCostModifier, ...] = ()


@dataclass(frozen=True)
class BlockMitigationInputs:
    direct_points: tuple[tuple[str, float], ...] = ()
    amount_blocked_modifiers: tuple[tuple[str, float], ...] = ()


class BlockStatCalculator:
    """Trace block stats with their verified non-generic ESO stacking rules."""

    BASE_BLOCK_COST = 1750.0
    BASE_BLOCK_MITIGATION = 0.50

    def block_cost(self, inputs: BlockCostInputs = BlockCostInputs()) -> DerivedStatTrace:
        trace = DerivedStatTrace(stat=StatId.BLOCK_COST)
        current = self.BASE_BLOCK_COST
        trace.add("base", "set", current, current)

        for label, amount in inputs.flat_reductions:
            current -= float(amount)
            trace.add(label, "subtract", float(amount), current)

        for modifier in inputs.sequential_modifiers:
            multiplier = 1.0 + float(modifier.percent)
            current *= multiplier
            trace.add(modifier.label, "multiply", multiplier, current)

        trace.raw_value = current
        trace.final_value = float(ceil(current))
        trace.add("ESO rounding", "ceil", trace.final_value, trace.final_value)
        return trace

    def block_mitigation(self, inputs: BlockMitigationInputs = BlockMitigationInputs()) -> DerivedStatTrace:
        trace = DerivedStatTrace(stat=StatId.BLOCK_MITIGATION)
        current = self.BASE_BLOCK_MITIGATION
        trace.add("base", "set", current, current)

        # Heavy Armor-style direct percentage points are the documented exception.
        for label, amount in inputs.direct_points:
            current += float(amount)
            trace.add(label, "add", float(amount), current)

        # "Amount of damage you can block" modifiers act on the base unblocked half.
        if inputs.amount_blocked_modifiers:
            total = sum(float(amount) for _label, amount in inputs.amount_blocked_modifiers)
            for label, amount in inputs.amount_blocked_modifiers:
                trace.add(label, "bucket", float(amount), current)
            added = self.BASE_BLOCK_MITIGATION * total
            current += added
            trace.add("amount-blocked modifiers", "add", added, current)

        trace.raw_value = current
        trace.final_value = current
        trace.add("ESO ratio", "retain", current, current)
        return trace
