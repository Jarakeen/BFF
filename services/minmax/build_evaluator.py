from .build import Build
from .build_evaluation import BuildEvaluation
from .calculation import StatEngine
from .combat_calculation import (
    CombatEffectResult,
    calculate_combat_effect,
)
from .combat_context import CombatContext
from .combat_contribution import (
    CombatContribution,
    calculate_combat_contribution,
)
from .combat_effect_evaluator import CombatEffectEvaluator
from .effect_kinds import EffectKind
from .evaluation_context import EvaluationContext
from .weapon_enchantment_effect_service import (
    WeaponEnchantmentEffectService,
)


class BuildEvaluator:
    """Evaluate a complete build under a specified combat context."""

    def __init__(
        self,
        *,
        stat_engine: StatEngine | None = None,
        weapon_enchantment_service: (
            WeaponEnchantmentEffectService | None
        ) = None,
    ):
        self.stat_engine = stat_engine or StatEngine()
        self.weapon_enchantment_service = (
            weapon_enchantment_service
        )
        self.combat_effect_evaluator = CombatEffectEvaluator()

    def evaluate(
            self,
            build: Build,
            context: EvaluationContext | None = None,
        ) -> BuildEvaluation:
            """Evaluate stats, combat effects, and contributions."""

            if context is None:
                context = EvaluationContext()

            stat_result = self.stat_engine.calculate(build)

            combat_context = CombatContext(
                fight_duration=context.fight_duration,
            )

            combat_effects: list[CombatEffectResult] = []
            combat_contributions: list[CombatContribution] = []

            if self.weapon_enchantment_service is not None:
                for weapon in build.weapons:
                    if weapon.enchantment_item_id is None:
                        continue

                    effects = (
                        self.weapon_enchantment_service.resolve_effects(
                            weapon.enchantment_item_id,
                            weapon_trait=weapon.trait,
                            weapon_quality=weapon.quality,
                        )
                    )

                    for effect in effects:
                        if not self.combat_effect_evaluator.is_applicable(
                            effect,
                            combat_context,
                        ):
                            continue

                        result = calculate_combat_effect(
                            effect,
                            fight_duration=context.fight_duration,
                        )

                        combat_effects.append(result)
                        combat_contributions.append(
                            calculate_combat_contribution(result)
                        )

            return BuildEvaluation(
                stats=stat_result,
                combat_effects=tuple(combat_effects),
                combat_contributions=tuple(combat_contributions),
            )