from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_canonical_healing_done_conditional_actual_heal_service import (
    ExtremeCanonicalHealingDoneConditionalActualHealService,
)
from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
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

    An explicitly requested Illuminate window also routes through the Templar
    adapter even when Dawn's Wrath is absent so the legality failure is preserved
    as evidence instead of becoming an unexpected constructor error. Inactive
    Illuminate-only kwargs are discarded for unrelated builds.

    Pure Nightblade builds use the dedicated Class Mastery adapter for
    target-health-dependent power math. All routes inherit the canonical
    conditional Healing Done path so generic sources such as Curative Curse and
    Healing Tides remain in one additive bucket with sheet, combat-state, CP, and
    reviewed bar Healing Done.

    Conditional Extreme builds use canonical per-component heal event identity by
    default. Proven recipient/time groups are scored independently, while skills
    without complete identity retain the reviewed legacy recipient/time guards.
    A caller-supplied healing-event service is preserved unchanged.
    """

    @staticmethod
    def create(
        build: PlayerBuild,
        *,
        target_health_fraction: float,
        **kwargs,
    ) -> ExtremeConditionalActualHealOptimizationService:
        illuminate_requested = bool(kwargs.get("illuminate_window_active", False))
        dawns_wrath_equipped = (
            ExtremeTemplarIlluminateCombatStateService.dawns_wrath_equipped(build)
        )
        if dawns_wrath_equipped or illuminate_requested:
            service_type = ExtremeTemplarConditionalActualHealService
        elif str(build.EsoClass or "").strip().casefold() == "nightblade":
            kwargs.pop("illuminate_window_active", None)
            kwargs.pop("templar_illuminate_state", None)
            service_type = ExtremeNightbladeConditionalActualHealService
        else:
            kwargs.pop("illuminate_window_active", None)
            kwargs.pop("templar_illuminate_state", None)
            service_type = ExtremeCanonicalHealingDoneConditionalActualHealService

        if "healing_events" not in kwargs:
            optimizer = kwargs.get("optimizer")
            database_path = getattr(optimizer, "database_path", None)
            kwargs["healing_events"] = ExtremeCanonicalHealingEventService(
                database_path=database_path
            )

        return service_type(
            target_health_fraction=target_health_fraction,
            **kwargs,
        )
