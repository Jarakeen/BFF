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


class ExtremeConditionalActualHealServiceFactory:
    """Select the reviewed conditional actual-heal optimizer for one build.

    Nightblade Class Mastery contains target-health-dependent power math that must
    be applied before heal coefficient evaluation. The dedicated Nightblade
    adapter owns that context rebuild while inheriting the canonical conditional
    Healing Done path.

    Other classes use the canonical Healing Done conditional optimizer so generic
    conditional sources such as Curative Curse and Healing Tides join sheet,
    combat-state, CP, and reviewed bar Healing Done before actual-effect
    evaluation. Routing on the base class remains harmless for Nightblades without
    a selected Class Mastery: the dedicated adapter resolves a zero mastery
    contribution and otherwise behaves like the canonical conditional service.
    """

    @staticmethod
    def create(
        build: PlayerBuild,
        *,
        target_health_fraction: float,
        **kwargs,
    ) -> ExtremeConditionalActualHealOptimizationService:
        service_type = (
            ExtremeNightbladeConditionalActualHealService
            if str(build.EsoClass or "").strip().casefold() == "nightblade"
            else ExtremeCanonicalHealingDoneConditionalActualHealService
        )
        return service_type(
            target_health_fraction=target_health_fraction,
            **kwargs,
        )
