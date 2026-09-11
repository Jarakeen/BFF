from __future__ import annotations

"""Apply the canonical active-Emperor maximum-resource passive.

This resolver owns only the shared mechanic projection. Runtime legality is
supplied explicitly through ``CombatState``; Extreme and other consumers must
choose the state they want to evaluate rather than inferring Emperor status from
build contents.
"""

from dataclasses import replace

from .base_character_state import PercentContribution, ResourceInputs
from .combat_state import CombatState
from .gear_stat_inputs import GearCalculationInputs


class EmperorPassiveInputResolver:
    """Project the Emperor passive onto Max Health/Magicka/Stamina inputs."""

    PASSIVE_NAME = "Emperor"
    SKILL_LINE = "Emperor"

    # Update 50 canonical tooltip values by owned Home Keeps.
    # The live tooltip groups 0/1 keeps into the same 38% tier.
    MAX_RESOURCE_PERCENT_BY_HOME_KEEPS = {
        0: 0.38,
        1: 0.38,
        2: 0.45,
        3: 0.53,
        4: 0.60,
        5: 0.68,
        6: 0.75,
    }

    @classmethod
    def percent_for_state(cls, combat_state: CombatState) -> float:
        if not combat_state.emperor_passive_active:
            return 0.0
        return cls.MAX_RESOURCE_PERCENT_BY_HOME_KEEPS[combat_state.emperor_home_keeps]

    @staticmethod
    def _apply_resource(
        inputs: ResourceInputs,
        *,
        percent: float,
    ) -> ResourceInputs:
        if percent <= 0.0:
            return inputs
        contribution = PercentContribution("Emperor", percent)
        return replace(
            inputs,
            skill_percent_contributions=(
                inputs.skill_percent_contributions + (contribution,)
            ),
        )

    @classmethod
    def apply(
        cls,
        result: GearCalculationInputs,
        *,
        combat_state: CombatState,
    ) -> GearCalculationInputs:
        percent = cls.percent_for_state(combat_state)
        if percent <= 0.0:
            return result
        return replace(
            result,
            health=cls._apply_resource(result.health, percent=percent),
            magicka=cls._apply_resource(result.magicka, percent=percent),
            stamina=cls._apply_resource(result.stamina, percent=percent),
            applied_effect_count=result.applied_effect_count + 3,
        )
