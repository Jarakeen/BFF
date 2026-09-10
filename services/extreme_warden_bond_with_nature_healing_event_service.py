from __future__ import annotations

from dataclasses import dataclass

from minmax.build_calculation_context import BuildCalculationContext
from minmax.combat_state import CombatState
from minmax.formulas.final_calculations import calculate_healing_total
from minmax.healing_received_combat_state import resolve_healing_received_combat_state
from minmax.runtime_event import RuntimeEvent
from minmax.stat_ids import StatId
from minmax.triggered_healing import TriggeredHealingEvent


@dataclass(frozen=True)
class ExtremeWardenBondWithNatureHealingEventResult:
    normal_event: TriggeredHealingEvent | None
    normal_heal: float | None
    critical_heal: float | None
    critical_healing_bonus: float | None
    critical_multiplier: float | None
    healing_received_ratio_points: float = 0.0
    healing_received_sources: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return (
            self.normal_event is not None
            and self.normal_heal is not None
            and self.critical_heal is not None
            and self.critical_healing_bonus is not None
            and self.critical_multiplier is not None
            and not self.unresolved
        )


class ExtremeWardenBondWithNatureHealingEventService:
    """Apply canonical healing modifiers to Bond with Nature's caster self-heal."""

    SOURCE = "Warden: Bond with Nature"
    CASTER_TARGET = "self"
    BASE_CRITICAL_HEALING = 0.50
    DEFAULT_CRITICAL_HEALING_CAP = 1.25

    @staticmethod
    def _derived_value(
        context: BuildCalculationContext,
        stat_id: StatId,
        *,
        label: str,
    ) -> tuple[float | None, tuple[str, ...]]:
        core_state = getattr(context, "core_state", None)
        if core_state is None:
            return None, (f"Bond with Nature {label} requires canonical core_state",)
        trace = core_state.derived.get(stat_id)
        if trace is None:
            return None, (f"Bond with Nature canonical {label} stat is unavailable",)
        return float(trace.final_value), ()

    def resolve(
        self,
        *,
        context: BuildCalculationContext,
        trigger_event: RuntimeEvent,
        base_self_heal: float,
    ) -> ExtremeWardenBondWithNatureHealingEventResult:
        base = float(base_self_heal)
        if base < 0.0:
            raise ValueError("Bond with Nature base_self_heal cannot be negative")

        healing_done, done_unresolved = self._derived_value(
            context, StatId.HEALING_DONE, label="Healing Done"
        )
        healing_taken, taken_unresolved = self._derived_value(
            context, StatId.HEALING_TAKEN, label="Healing Taken"
        )
        critical_healing, critical_unresolved = self._derived_value(
            context, StatId.CRITICAL_HEALING, label="Critical Healing"
        )
        unresolved = tuple(
            dict.fromkeys((*done_unresolved, *taken_unresolved, *critical_unresolved))
        )
        combat_state = getattr(context, "combat_state", CombatState())
        healing_received = resolve_healing_received_combat_state(combat_state)
        if unresolved:
            return ExtremeWardenBondWithNatureHealingEventResult(
                normal_event=None,
                normal_heal=None,
                critical_heal=None,
                critical_healing_bonus=critical_healing,
                critical_multiplier=None,
                healing_received_ratio_points=healing_received.ratio_points,
                healing_received_sources=healing_received.sources,
                unresolved=unresolved,
            )

        assert healing_done is not None
        assert healing_taken is not None
        assert critical_healing is not None
        healing_multiplier = calculate_healing_total(
            healing_done=healing_done,
            healing_taken=healing_taken,
            healing_received=healing_received.ratio_points,
        )
        normal = base * healing_multiplier
        total_critical_bonus = min(
            self.BASE_CRITICAL_HEALING + critical_healing,
            self.DEFAULT_CRITICAL_HEALING_CAP,
        )
        critical_multiplier = 1.0 + total_critical_bonus
        critical = normal * critical_multiplier
        event = TriggeredHealingEvent(
            time_seconds=trigger_event.time_seconds,
            amount=normal,
            source=self.SOURCE,
            target=self.CASTER_TARGET,
        )
        return ExtremeWardenBondWithNatureHealingEventResult(
            normal_event=event,
            normal_heal=normal,
            critical_heal=critical,
            critical_healing_bonus=max(
                0.0, total_critical_bonus - self.BASE_CRITICAL_HEALING
            ),
            critical_multiplier=critical_multiplier,
            healing_received_ratio_points=healing_received.ratio_points,
            healing_received_sources=healing_received.sources,
            unresolved=(),
        )
