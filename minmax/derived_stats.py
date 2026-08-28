from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil

from .stat_ids import StatId


@dataclass(frozen=True)
class StatContribution:
    label: str
    value: float


@dataclass(frozen=True)
class DerivedStatInputs:
    """Explicit contributions to a derived combat stat.

    Contributions are deliberately separated so a calculation trace can show
    exactly where a result came from. Unverified ESO-specific rules should be
    represented as inputs until their formula is established by the project's
    math references and in-game testing.
    """

    level: float = 50.0
    flat: tuple[StatContribution, ...] = ()
    percent: tuple[StatContribution, ...] = ()
    additive_after_percent: tuple[StatContribution, ...] = ()


@dataclass
class DerivedStatTrace:
    stat: StatId
    steps: list[tuple[str, str, float, float]] = field(default_factory=list)
    raw_value: float = 0.0
    final_value: float = 0.0

    def add(self, label: str, operation: str, value: float, result: float) -> None:
        self.steps.append((label, operation, value, result))


class DerivedStatCalculator:
    """Traceable first layer for derived combat stats.

    ESO stores several stats as ratios internally. In particular, critical
    chance and critical damage are represented here as 0.10 / 0.50 rather than
    10 / 50. Integer-facing stats continue to use ESO's ceiling behavior.
    This keeps the calculation layer numerically correct and lets the UI
    format ratio stats as percentages without multiplying an already-rounded
    value by 100.
    """

    RATIO_STATS = frozenset(
        {
            StatId.CRITICAL_CHANCE,
            StatId.CRITICAL_DAMAGE,
            StatId.HEALING_DONE,
            StatId.HEALING_TAKEN,
        }
    )

    @staticmethod
    def eso_round(value: float) -> int:
        return int(ceil(value))

    def _finalize(self, trace: DerivedStatTrace) -> DerivedStatTrace:
        trace.raw_value = trace.raw_value
        if trace.stat in self.RATIO_STATS:
            # Ratio stats must retain their fractional value. Applying ceil to
            # 0.10 would turn 10% Critical Chance into 100% when formatted.
            trace.final_value = trace.raw_value
            trace.add("ESO ratio", "retain", trace.raw_value, trace.final_value)
        else:
            trace.final_value = self.eso_round(trace.raw_value)
            trace.add("ESO rounding", "ceil", trace.final_value, trace.final_value)
        return trace

    def _flat_percent(
        self,
        stat: StatId,
        base: float,
        inputs: DerivedStatInputs,
    ) -> DerivedStatTrace:
        trace = DerivedStatTrace(stat=stat)
        current = base
        trace.add("base", "set", base, current)

        for contribution in inputs.flat:
            current += contribution.value
            trace.add(contribution.label, "add", contribution.value, current)

        multiplier = 1.0
        for contribution in inputs.percent:
            multiplier += contribution.value
        if multiplier != 1.0:
            current *= multiplier
            trace.add("percentage modifiers", "multiply", multiplier, current)

        for contribution in inputs.additive_after_percent:
            current += contribution.value
            trace.add(contribution.label, "add", contribution.value, current)

        trace.raw_value = current
        return self._finalize(trace)

    def weapon_damage(self, inputs: DerivedStatInputs = DerivedStatInputs()) -> DerivedStatTrace:
        return self._flat_percent(
            StatId.WEAPON_DAMAGE,
            20.0 * inputs.level,
            inputs,
        )

    def spell_damage(self, inputs: DerivedStatInputs = DerivedStatInputs()) -> DerivedStatTrace:
        return self._flat_percent(
            StatId.SPELL_DAMAGE,
            20.0 * inputs.level,
            inputs,
        )

    def resolved_stat(
        self,
        stat: StatId,
        *,
        base: float = 0.0,
        inputs: DerivedStatInputs = DerivedStatInputs(),
    ) -> DerivedStatTrace:
        """Aggregate a stat whose ESO formula is supplied by the caller.

        This is intentionally useful for resistance, penetration, critical,
        and similar stats without pretending their version-sensitive formulas
        are already verified.
        """
        return self._flat_percent(stat, base, inputs)
