from dataclasses import dataclass, field

from services.minmax.build import Build
from services.minmax.effects import Effect, EffectOperation
from services.minmax.stat_ids import StatId
from services.minmax.effect_kinds import EffectKind

@dataclass
class StatBreakdown:
    base: float = 0.0
    additive: float = 0.0
    multiplicative: float = 1.0

    sources: list[Effect] = field(default_factory=list)

    @property
    def final(self) -> float:
        return (self.base + self.additive) * self.multiplicative


@dataclass
class CalculationResult:
    stats: dict[StatId, StatBreakdown]

    def value(self, stat: StatId) -> float:
        breakdown = self.stats.get(stat)

        if breakdown is None:
            return 0.0

        return breakdown.final


class StatEngine:

    def calculate(self, build: Build) -> CalculationResult:
        state: dict[StatId, StatBreakdown] = {}

        for stat_name, value in build.base_stats.items():
            stat = StatId(stat_name)

            state[stat] = StatBreakdown(
                base=value
            )

        for effect in build.effects:

            if effect.kind != EffectKind.STAT:
                continue

            if effect.stat is None:
                raise ValueError(
                    f"Stat effect has no stat: {effect.source!r}"
                )

            breakdown = state.setdefault(
                effect.stat,
                StatBreakdown()
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
                    f"Unsupported effect operation: "
                    f"{effect.operation}"
                )
        return CalculationResult(stats=state)