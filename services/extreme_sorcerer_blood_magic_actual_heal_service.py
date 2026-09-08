from __future__ import annotations

from dataclasses import dataclass

from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
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
        # Blood Magic value/trigger identity can be complete while critical
        # eligibility remains intentionally unresolved for the global critical
        # Actual Heal objective.
        return bool(
            self.optimized_event.trigger_satisfied
            and self.optimized_event.normal_heal is not None
            and not self.unresolved
        )


class ExtremeSorcererBloodMagicActualHealService:
    """Optimize the reviewed U50 Blood Magic normal-heal event through Max Health.

    Blood Magic is not a coefficient-bearing cast heal. At reviewed U50 rank 2 it
    is a separate self-heal event equal to 10% of Max Health when a costed Dark
    Magic ability is cast while the caster is below full Health. The ordinary
    Extreme Actual Heal optimizer therefore must not attach it to some unrelated
    selected heal skill.

    This first optimization lane deliberately reuses the canonical sheet-stat
    ``max_health`` objective. Its search is consequently a lower bound relative
    to the broader Actual Heal whole-build search, which additionally explores
    race and reviewed gear-package replacement. Those omitted surfaces remain
    explicit until a shared candidate-search abstraction can be reused safely.

    Critical eligibility is not inferred. This service produces a proved normal
    Blood Magic heal candidate; it does not yet claim a MOST Critical Heal value.
    """

    EXTRA_SEARCH_SCOPE = (
        "Blood Magic U50 rank-2 trigger: costed Dark Magic cast while caster is below full Health",
        "Blood Magic U50 rank-2 heal amount: 10% of canonical Max Health",
        "separate self-heal event; not attached to the triggering ability's own heal/damage event",
    )
    EXTRA_OMITTED_SCOPE = (
        "Blood Magic critical-heal eligibility",
        "race replacement beyond the canonical max-health sheet optimizer",
        "reviewed gear-set/package replacement beyond the canonical max-health sheet optimizer",
        "full legal Dark Magic trigger-cast enumeration within each subclass route",
    )

    def __init__(
        self,
        *,
        optimizer: ExtremeCompleteOptimizationService | None = None,
        triggered_heals: ExtremeSorcererTriggeredHealService | None = None,
    ) -> None:
        self.optimizer = optimizer or ExtremeCompleteOptimizationService()
        self.triggered_heals = triggered_heals or ExtremeSorcererTriggeredHealService()

    def optimize(
        self,
        baseline_build: PlayerBuild,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
    ) -> ExtremeSorcererBloodMagicActualHealResult:
        sheet = self.optimizer.optimize(
            baseline_build,
            "max_health",
            active_bar=active_bar,
            max_passes=max_passes,
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
