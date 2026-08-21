from .combat_context import CombatContext
from .combat_effects import CombatEffect


class CombatEffectEvaluator:
    """Determine whether a combat effect applies in a combat context."""

    def is_applicable(
        self,
        effect: CombatEffect,
        context: CombatContext,
    ) -> bool:
        if effect.target is not None:
            if context.target != effect.target:
                return False

        if effect.condition is not None:
            if not context.is_active(effect.condition):
                return False

        return True