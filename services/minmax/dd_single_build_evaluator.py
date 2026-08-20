from dataclasses import dataclass

from .build import Build
from .build_evaluation import BuildEvaluation
from .build_evaluator import BuildEvaluator
from .dd_damage import (
    DDDamageEvent,
    DDDamageResult,
    calculate_dd_damage,
)
from .dd_mitigation import calculate_dd_mitigation
from .dd_stat_evaluation import (
    DDStatEvaluation,
    evaluate_dd_stats,
)
from .evaluation_context import EvaluationContext


@dataclass(frozen=True)
class DDBuildEvaluation:
    """Complete DD evaluation of a single build."""

    build_evaluation: BuildEvaluation
    dd_stats: DDStatEvaluation
    damage: DDDamageResult


class DDBuildEvaluator:
    """
    Evaluate a build through the complete DD pipeline.

    The generic BuildEvaluator remains responsible for resolving
    the build. This class adapts that result into the DD-specific
    stat and damage evaluation layers.
    """

    def __init__(
        self,
        *,
        build_evaluator: BuildEvaluator | None = None,
    ):
        self.build_evaluator = (
            build_evaluator or BuildEvaluator()
        )

    def evaluate(
        self,
        build: Build,
        event: DDDamageEvent,
        context: EvaluationContext | None = None,
    ) -> DDBuildEvaluation:
        """Evaluate one build against one modeled DD event."""

        if context is None:
            context = EvaluationContext()

        build_evaluation = self.build_evaluator.evaluate(
            build,
            context,
        )

        dd_stats = evaluate_dd_stats(
            build_evaluation.stats,
            context,
        )

        # First resolve the event without mitigation.
        #
        # This lets the existing DD damage calculation determine
        # the correct penetration stat from the damage profile.
        # We deliberately do not duplicate that mapping here.
        raw_damage = calculate_dd_damage(
            event,
            dd_stats,
        )

        mitigation = None

        if (
            context.target_resistance is not None
            and raw_damage.penetration_stat is not None
        ):
            mitigation = calculate_dd_mitigation(
                target_resistance=context.target_resistance,
                penetration=raw_damage.penetration,
            )

        damage = calculate_dd_damage(
            event,
            dd_stats,
            mitigation=mitigation,
        )

        return DDBuildEvaluation(
            build_evaluation=build_evaluation,
            dd_stats=dd_stats,
            damage=damage,
        )