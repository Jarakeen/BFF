from __future__ import annotations

from dataclasses import dataclass

from .build_calculation_context import BuildCalculationContext
from .calculation import CalculationResult, StatBreakdown
from .dd_damage import DDDamageEvent, DDDamageResult, calculate_dd_damage
from .dd_mitigation import calculate_dd_mitigation
from .dd_stat_evaluation import DDStatEvaluation, evaluate_dd_stats
from .evaluation_context import EvaluationContext
from .stat_ids import StatId


@dataclass(frozen=True)
class ModeledDamagePotency:
    """One authoritative DD metric supplied to Phase 12 orchestration.

    The value may represent a verified single event or another explicitly named
    damage metric. It is not automatically raid DPS or a rotation ceiling.
    """

    value: float | None
    metric_name: str
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    damage: DDDamageResult | None = None
    dd_stats: DDStatEvaluation | None = None

    def __post_init__(self) -> None:
        if not self.metric_name.strip():
            raise ValueError("Damage metric_name is required.")
        if self.value is not None and self.value < 0:
            raise ValueError("Damage metric value cannot be negative.")

    @property
    def resolved(self) -> bool:
        return self.value is not None and not self.unresolved


def calculation_result_from_build_context(
    context: BuildCalculationContext,
) -> CalculationResult | None:
    """Project canonical core stats into the existing DD stat evaluator."""

    if context.core_state is None:
        return None

    percent_stats = {StatId.CRITICAL_CHANCE, StatId.CRITICAL_DAMAGE}
    stats: dict[StatId, StatBreakdown] = {}
    for stat in (
        StatId.WEAPON_DAMAGE,
        StatId.SPELL_DAMAGE,
        StatId.PHYSICAL_PENETRATION,
        StatId.SPELL_PENETRATION,
        StatId.CRITICAL_CHANCE,
        StatId.CRITICAL_DAMAGE,
    ):
        trace = context.core_state.derived.get(stat)
        value = float(trace.final_value) if trace is not None else 0.0
        if stat in percent_stats:
            value *= 100.0
        stats[stat] = StatBreakdown(base=value)
    return CalculationResult(stats=stats)


def measure_modeled_damage_potency(
    *,
    context: BuildCalculationContext,
    event: DDDamageEvent,
    evaluation_context: EvaluationContext,
) -> ModeledDamagePotency:
    """Evaluate one explicit event through canonical static and DD math."""

    calculation = calculation_result_from_build_context(context)
    if calculation is None:
        return ModeledDamagePotency(
            value=None,
            metric_name="canonical single-event expected damage",
            unresolved=("Canonical static context has no resolved core stat state.",),
        )

    dd_stats = evaluate_dd_stats(calculation, evaluation_context)
    raw_damage = calculate_dd_damage(event, dd_stats)
    mitigation = None
    if (
        evaluation_context.target_resistance is not None
        and raw_damage.penetration_stat is not None
    ):
        mitigation = calculate_dd_mitigation(
            target_resistance=evaluation_context.target_resistance,
            penetration=raw_damage.penetration,
        )
    damage = calculate_dd_damage(event, dd_stats, mitigation=mitigation)

    event_type = event.damage_type or "untyped"
    evidence = (
        f"metric=canonical single-event expected damage",
        f"event base={event.base_value:g}; scaling={event.scaling_coefficient:g}; type={event_type}",
        f"offensive stat={damage.offensive_stat}; power={damage.offensive_power:g}",
        f"critical chance={damage.critical_chance:.6f}; critical damage={damage.critical_damage:.6f}",
        f"penetration={damage.penetration:g}; mitigation multiplier={damage.mitigation_multiplier:.6f}",
        f"final expected damage={damage.final_damage:.6f}",
    )
    return ModeledDamagePotency(
        value=damage.final_damage,
        metric_name="canonical single-event expected damage",
        evidence=evidence,
        damage=damage,
        dd_stats=dd_stats,
    )
