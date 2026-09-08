from __future__ import annotations

from models.build_model import PlayerBuild
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
    adapter owns that context rebuild while inheriting every generic conditional
    mechanic from ``ExtremeConditionalActualHealOptimizationService``.

    Other classes continue to use the generic conditional optimizer. Routing on
    the base class is intentionally harmless for Nightblades without a selected
    Class Mastery: the dedicated adapter resolves a zero mastery contribution and
    otherwise behaves like the generic service.
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
            else ExtremeConditionalActualHealOptimizationService
        )
        return service_type(
            target_health_fraction=target_health_fraction,
            **kwargs,
        )
