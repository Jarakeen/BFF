from __future__ import annotations

"""First deterministic Phase 14 combat-simulation kernel.

This slice proves deterministic orchestration and bar-state progression over the
canonical Phase 13 RotationPlan. ESO consequences that are not yet connected are
reported explicitly as unresolved instead of being treated as zero.
"""

from models.combat_simulation import (
    CombatSimulationEvent,
    CombatSimulationResult,
    SimulationEventPriority,
)
from models.effective_build_snapshot import EffectiveBuildSnapshot
from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationActionKind, RotationPlan

from services.combat_simulation_event_queue import CombatSimulationEventQueue


_CONSEQUENCE_PENDING = frozenset(
    {
        RotationActionKind.SKILL,
        RotationActionKind.LIGHT_ATTACK,
        RotationActionKind.HEAVY_ATTACK,
        RotationActionKind.ULTIMATE,
        RotationActionKind.POTION,
        RotationActionKind.BLOCK,
        RotationActionKind.DODGE,
    }
)


class CombatSimulationService:
    """Replay one exact build + rotation into a deterministic event stream."""

    def __init__(
        self,
        *,
        active_bar_assessor: RotationActiveBarAssessor | None = None,
    ) -> None:
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()

    def simulate(
        self,
        *,
        build_snapshot: EffectiveBuildSnapshot,
        plan: RotationPlan,
        initial_bar: str = "front",
    ) -> CombatSimulationResult:
        if not isinstance(build_snapshot, EffectiveBuildSnapshot):
            raise TypeError("combat simulation requires EffectiveBuildSnapshot")
        if not isinstance(plan, RotationPlan):
            raise TypeError("combat simulation requires RotationPlan")

        build = build_snapshot.materialize()
        if plan.character_name.casefold() != str(build.Name or "").strip().casefold():
            raise ValueError("rotation character does not match effective build")
        if plan.build_name.casefold() != str(build.BuildName or "").strip().casefold():
            raise ValueError("rotation build does not match effective build")

        assessment = self.active_bar_assessor.assess(plan, initial_bar=initial_bar)
        unresolved: list[str] = list(plan.unresolved)
        for violation in assessment.violations:
            unresolved.append(
                f"{violation.time_seconds:g}s {violation.action_name}: {violation.reason}"
            )

        queue = CombatSimulationEventQueue()
        for action in plan.actions:
            queue.push(
                CombatSimulationEvent(
                    time_seconds=float(action.time_seconds),
                    priority=int(SimulationEventPriority.ACTION),
                    sequence=int(action.sequence),
                    event_type="action",
                    source=str(action.name or action.kind.value),
                    payload=(
                        ("kind", action.kind.value),
                        ("bar", action.bar or ""),
                        ("target_key", action.target_key or ""),
                    ),
                )
            )

        events: list[CombatSimulationEvent] = []
        while queue:
            event = queue.pop()
            if event.time_seconds > plan.duration_seconds:
                break
            events.append(event)

            kind = RotationActionKind(event.payload_dict()["kind"])
            if kind in _CONSEQUENCE_PENDING:
                unresolved.append(
                    f"{event.time_seconds:g}s {event.source}: "
                    f"{kind.value} consequence projection not yet wired in Phase 14"
                )

        return CombatSimulationResult(
            duration_seconds=plan.duration_seconds,
            initial_bar=assessment.initial_bar,
            final_bar=assessment.final_bar,
            events=tuple(events),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = ["CombatSimulationService"]
