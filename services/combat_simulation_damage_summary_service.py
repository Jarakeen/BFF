from __future__ import annotations

"""Read-only damage summary for one completed Combat Simulation result."""

from dataclasses import dataclass

from models.combat_simulation import CombatSimulationResult


@dataclass(frozen=True)
class CombatSimulationDamageSourceSummary:
    source: str
    event_count: int
    attempted_damage: float


@dataclass(frozen=True)
class CombatSimulationDamageSummary:
    duration_seconds: float
    outgoing_event_count: int
    attempted_damage: float
    applied_damage: float
    ending_target_health: int | None
    target_maximum_health: int | None
    target_dead: bool
    death_time_seconds: float | None
    damage_by_source: tuple[CombatSimulationDamageSourceSummary, ...]
    unresolved: tuple[str, ...]

    @property
    def complete_damage_evidence(self) -> bool:
        return not self.unresolved

    @property
    def modeled_dps(self) -> float | None:
        if not self.complete_damage_evidence or self.duration_seconds <= 0.0:
            return None
        return self.applied_damage / self.duration_seconds


class CombatSimulationDamageSummaryService:
    """Summarize event-stream damage without altering simulation truth."""

    def summarize(
        self,
        result: CombatSimulationResult,
        *,
        target_identity: str,
    ) -> CombatSimulationDamageSummary:
        target = str(target_identity or "").strip()
        if not target:
            raise ValueError("combat simulation damage summary target identity is required")

        outgoing = tuple(
            event
            for event in result.events
            if event.event_type == "outgoing_damage"
            and str(event.payload_dict().get("recipient") or "").strip() == target
        )
        health = tuple(
            event
            for event in result.events
            if event.event_type == "health_change"
            and str(event.payload_dict().get("recipient") or "").strip() == target
        )
        deaths = tuple(
            event
            for event in result.events
            if event.event_type == "death"
            and str(event.payload_dict().get("recipient") or "").strip() == target
        )

        source_totals: dict[str, list[float]] = {}
        for event in outgoing:
            payload = event.payload_dict()
            source = str(event.source or "unknown").strip() or "unknown"
            row = source_totals.setdefault(source, [0.0, 0.0])
            row[0] += 1.0
            row[1] += float(payload.get("amount") or 0.0)

        combatant = (
            result.target_state.combatant(target)
            if result.target_state is not None
            else None
        )
        maximum = (
            int(combatant.maximum_health)
            if combatant is not None and combatant.maximum_health is not None
            else None
        )
        starting = (
            int(combatant.current_health)
            if combatant is not None and combatant.current_health is not None
            else None
        )
        ending = starting
        if health:
            ending = int(health[-1].payload_dict().get("after") or 0)

        return CombatSimulationDamageSummary(
            duration_seconds=float(result.duration_seconds),
            outgoing_event_count=len(outgoing),
            attempted_damage=sum(
                float(event.payload_dict().get("amount") or 0.0)
                for event in outgoing
            ),
            applied_damage=sum(
                float(event.payload_dict().get("applied_damage") or 0.0)
                for event in health
            ),
            ending_target_health=ending,
            target_maximum_health=maximum,
            target_dead=bool(deaths) or ending == 0,
            death_time_seconds=(
                float(deaths[0].time_seconds)
                if deaths
                else None
            ),
            damage_by_source=tuple(
                CombatSimulationDamageSourceSummary(
                    source=source,
                    event_count=int(values[0]),
                    attempted_damage=float(values[1]),
                )
                for source, values in sorted(
                    source_totals.items(),
                    key=lambda item: (-item[1][1], item[0].casefold()),
                )
            ),
            unresolved=tuple(result.unresolved),
        )


__all__ = [
    "CombatSimulationDamageSourceSummary",
    "CombatSimulationDamageSummary",
    "CombatSimulationDamageSummaryService",
]
