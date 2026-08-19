from dataclasses import dataclass, field

from .build import Build
from .calculation_context import CalculationContext
from .effect_kinds import EffectKind
from .effects import Effect, EffectOperation
from .stat_ids import StatId


@dataclass
class StatBreakdown:
    base: float = 0.0
    additive: float = 0.0
    multiplicative: float = 0.0
    final: float = 0.0
    sources: list[Effect] = field(default_factory=list)

    @property
    def total(self) -> float:
        return (self.base + self.additive) * (1 + self.multiplicative)


@dataclass
class CalculationResult:
    stats: dict[StatId, StatBreakdown]

    def value(self, stat: StatId) -> float:
        breakdown = self.stats.get(stat)

        if breakdown is None:
            return 0.0

        return breakdown.total


class StatEngine:
    def calculate(
        self,
        build: Build,
        context: CalculationContext | None = None,
    ) -> CalculationResult:
        if context is None:
            context = CalculationContext()

        state: dict[StatId, StatBreakdown] = {}

        # Base stats
        for stat_name, value in build.base_stats.items():
            stat = StatId(stat_name)
            state[stat] = StatBreakdown(
                base=value,
            )

        # Effects
        for effect in build.effects:
            if effect.kind != EffectKind.STAT:
                continue

            # Conditional effects are only active when their
            # condition is satisfied by the calculation context.
            if effect.condition is not None:
                if not context.is_active(effect.condition):
                    continue

            if effect.stat is None:
                raise ValueError(
                    f"Stat effect has no stat: {effect.source!r}"
                )

            breakdown = state.setdefault(
                effect.stat,
                StatBreakdown(),
            )

            breakdown.sources.append(effect)

            if effect.operation == EffectOperation.ADD:
                breakdown.additive += effect.value

            elif effect.operation == EffectOperation.ADD_PERCENT:
                breakdown.multiplicative += effect.value / 100.0

            elif effect.operation == EffectOperation.MULTIPLY:
                breakdown.multiplicative *= effect.value

            elif effect.operation == EffectOperation.SET:
                breakdown.base = effect.value

            else:
                raise ValueError(
                    f"Unsupported effect operation: {effect.operation}"
                )

        return CalculationResult(stats=state)