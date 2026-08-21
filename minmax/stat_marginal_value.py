from dataclasses import dataclass

from .build import Build
from .dd_damage import DDDamageEvent
from .dd_single_build_evaluator import DDBuildEvaluator
from .evaluation_context import EvaluationContext
from .stat_ids import StatId


@dataclass(frozen=True)
class StatMarginalValue:
    """Measured value of increasing one build stat."""

    stat: StatId
    delta: float

    baseline_damage: float
    modified_damage: float

    absolute_change: float
    relative_change: float

    value_per_unit: float


def calculate_stat_marginal_value(
    build: Build,
    *,
    stat: StatId,
    delta: float,
    event: DDDamageEvent,
    context: EvaluationContext | None = None,
    evaluator: DDBuildEvaluator | None = None,
) -> StatMarginalValue:
    """
    Measure the damage change caused by increasing one stat.

    The existing DD evaluation pipeline remains the single source
    of truth for damage calculation.
    """

    if delta <= 0:
        raise ValueError(
            "Stat delta must be greater than zero."
        )

    if context is None:
        context = EvaluationContext()

    if evaluator is None:
        evaluator = DDBuildEvaluator()

    baseline = evaluator.evaluate(
        build,
        event,
        context,
    )

    modified_build = _copy_build(build)

    current_value = modified_build.base_stats.get(
        stat.value,
        0.0,
    )

    modified_build.base_stats[stat.value] = (
        current_value + delta
    )

    modified = evaluator.evaluate(
        modified_build,
        event,
        context,
    )

    baseline_damage = baseline.damage.mitigated_damage
    modified_damage = modified.damage.mitigated_damage

    absolute_change = (
        modified_damage - baseline_damage
    )

    if baseline_damage == 0:
        relative_change = 0.0
    else:
        relative_change = (
            absolute_change / baseline_damage
        )

    value_per_unit = (
        absolute_change / delta
    )

    return StatMarginalValue(
        stat=stat,
        delta=delta,
        baseline_damage=baseline_damage,
        modified_damage=modified_damage,
        absolute_change=absolute_change,
        relative_change=relative_change,
        value_per_unit=value_per_unit,
    )


def _copy_build(build: Build) -> Build:
    """Create an independent copy of a build for perturbation."""

    return Build(
        name=build.name,
        race_id=build.race_id,
        base_stats=dict(build.base_stats),
        gear_sets=list(build.gear_sets),
        armor_glyphs=list(build.armor_glyphs),
        weapons=list(build.weapons),
        effects=list(build.effects),
    )