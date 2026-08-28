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
    final_value: int = 0

    def add(self, label: str, operation: str, value: float, result: float) -> None:
        self.steps.append((label, operation, value, result))


class DerivedStatCalculator:
    """Traceable first layer for derived combat stats.

    The level-based Weapon/Spell Damage baseline is kept explicit here. Other
    derived stats use supplied resolved contributions until their live-game
    formula has been verified. This prevents the calculator from silently
    inventing rules for ambiguous or version-sensitive ESO mechanics.
    """

    @staticmethod
    def eso_round(value: float) -> int:
        return int(ceil(value))

    @staticmethod
    def _flat_percent(
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
        trace.final_value = DerivedStatCalculator.eso_round(current)
        trace.add("ESO rounding", "ceil", trace.final_value, trace.final_value)
        return trace

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
