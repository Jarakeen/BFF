from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_canonical_healing_done_conditional_actual_heal_service import (
    ExtremeCanonicalHealingDoneConditionalActualHealService,
)
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_nightblade_conditional_actual_heal_service import (
    ExtremeNightbladeConditionalActualHealService,
)
from services.extreme_templar_conditional_actual_heal_service import (
    ExtremeTemplarConditionalActualHealService,
)
from services.extreme_templar_illuminate_combat_state_service import (
    ExtremeTemplarIlluminateCombatStateService,
)


class ExtremeConditionalActualHealServiceFactory:
    """Select the reviewed conditional actual-heal optimizer for one build.

    Builds with an equipped Dawn's Wrath class line use the Templar adapter so
    reviewed Illuminate Minor Sorcery can modify Spell Damage before coefficient
    evaluation. This includes legal foreign-class subclass routes. A Nightblade
    carrying Dawn's Wrath is necessarily subclassed, so Class Mastery is disabled
    and the Templar route correctly takes precedence over the pure-Nightblade
    Class Mastery adapter.

    Pure Nightblade builds use the dedicated Class Mastery adapter for
    target-health-dependent power math. All routes inherit the canonical
    conditional Healing Done path so generic sources such as Curative Curse and
    Healing Tides remain in one additive bucket with sheet, combat-state, CP, and
    reviewed bar Healing Done.
    """

    @staticmethod
    def create(
        build: PlayerBuild,
        *,
        target_health_fraction: float,
        **kwargs,
    ) -> ExtremeConditionalActualHealOptimizationService:
        if ExtremeTemplarIlluminateCombatStateService.dawns_wrath_equipped(build):
            service_type = ExtremeTemplarConditionalActualHealService
        elif str(build.EsoClass or "").strip().casefold() == "nightblade":
            service_type = ExtremeNightbladeConditionalActualHealService
        else:
            service_type = ExtremeCanonicalHealingDoneConditionalActualHealService
        return service_type(
            target_health_fraction=target_health_fraction,
            **kwargs,
        )
