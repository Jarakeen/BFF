from __future__ import annotations

from dataclasses import dataclass

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_route_aware_whole_build_max_health_optimization_service import (
    ExtremeRouteAwareWholeBuildMaxHealthOptimizationService,
)
from services.extreme_sorcerer_triggered_heal_service import (
    ExtremeSorcererTriggeredHealResult,
    ExtremeSorcererTriggeredHealService,
)


@dataclass(frozen=True)
class ExtremeSorcererBloodMagicActualHealResult:
    baseline_build: PlayerBuild
    optimized_build: PlayerBuild
    baseline_max_health: float
    optimized_max_health: float
    baseline_event: ExtremeSorcererTriggeredHealResult
    optimized_event: ExtremeSorcererTriggeredHealResult
    unresolved: tuple[str, ...]
    search_scope: tuple[str, ...]
    omitted_scope: tuple[str, ...]

    @property
    def normal_heal_gain(self) -> float:
        before = float(self.baseline_event.normal_heal or 0.0)
        after = float(self.optimized_event.normal_heal or 0.0)
        return after - before

    @property
    def mechanic_complete(self) -> bool:
        return bool(
            self.optimized_event.trigger_satisfied
            and self.optimized_event.normal_heal is not None
            and not self.unresolved
        )


class ExtremeSorcererBloodMagicActualHealService:
    """Optimize the reviewed U50 Blood Magic heal event through Max Health.

    Blood Magic is a separate self-heal event equal to 10% of Max Health when a
    costed Dark Magic ability is cast while the caster is below full Health. The
    default optimizer searches canonical Max Health across ordinary sheet
    mutations plus reviewed race/set/package replacements.

    Route callers may provide the exact hypothetical progression snapshot created
    for a subclass configuration. That snapshot is preserved through every
    candidate reevaluation so class-line passives are evaluated for the route
    being scored rather than for the original saved build.

    Blood Magic is a Max-Health-scaled passive proc. The project's reviewed proc
    critical policy therefore marks the event non-critical; its maximum event is
    the proved normal-heal value, not a fabricated critical variant.
    """

    EXTRA_SEARCH_SCOPE = (
        "Blood Magic U50 rank-2 trigger: costed Dark Magic cast while caster is below full Health",
        "Blood Magic U50 rank-2 heal amount: 10% of canonical Max Health",
        "Blood Magic Max-Health passive-proc critical policy: non-critical",
        "separate self-heal event; not attached to the triggering ability's own heal/damage event",
    )
    EXTRA_OMITTED_SCOPE = (
        "full legal Dark Magic trigger-cast enumeration within each subclass route",
    )

    def __init__(
        self,
        *,
        optimizer: ExtremeCompleteOptimizationService | None = None,
        triggered_heals: ExtremeSorcererTriggeredHealService | None = None,
    ) -> None:
        self.optimizer = (
            optimizer
            if optimizer is not None
            else ExtremeRouteAwareWholeBuildMaxHealthOptimizationService()
        )
        self.triggered_heals = (
            triggered_heals
            if triggered_heals is not None
            else ExtremeSorcererTriggeredHealService()
        )

    def optimize(
        self,
        baseline_build: PlayerBuild,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
        progression_override: CharacterProgression | None = None,
    ) -> ExtremeSorcererBloodMagicActualHealResult:
        optimizer_kwargs = {
            "active_bar": active_bar,
            "max_passes": max_passes,
        }
        if progression_override is not None:
            optimizer_kwargs["progression_override"] = progression_override
        sheet = self.optimizer.optimize(
            baseline_build,
            "max_health",
            **optimizer_kwargs,
        )
        baseline_event = self.triggered_heals.resolve(
            ability_name="Blood Magic",
            dark_magic_ability_cast_with_cost=True,
            caster_at_full_health=False,
            max_health=float(sheet.baseline_value),
        )
        optimized_event = self.triggered_heals.resolve(
            ability_name="Blood Magic",
            dark_magic_ability_cast_with_cost=True,
            caster_at_full_health=False,
            max_health=float(sheet.optimized_value),
        )
        unresolved = tuple(
            dict.fromkeys(
                message
                for message in (
                    *tuple(sheet.unresolved),
                    *baseline_event.unresolved,
                    *optimized_event.unresolved,
                )
                if message
            )
        )
        return ExtremeSorcererBloodMagicActualHealResult(
            baseline_build=sheet.baseline_build,
            optimized_build=sheet.optimized_build,
            baseline_max_health=float(sheet.baseline_value),
            optimized_max_health=float(sheet.optimized_value),
            baseline_event=baseline_event,
            optimized_event=optimized_event,
            unresolved=unresolved,
            search_scope=(*self.EXTRA_SEARCH_SCOPE, *tuple(sheet.search_scope)),
            omitted_scope=(*self.EXTRA_OMITTED_SCOPE, *tuple(sheet.omitted_scope)),
        )
