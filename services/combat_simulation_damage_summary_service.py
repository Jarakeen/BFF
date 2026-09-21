from __future__ import annotations

"""Read-only damage summary for one completed Combat Simulation result."""

from dataclasses import dataclass
from math import isfinite

from models.combat_simulation import CombatSimulationResult


@dataclass(frozen=True)
class CombatSimulationDamageSourceSummary:
    source: str
    event_count: int
    attempted_damage: float
    applied_damage: float
    overkill: float
    killing_blow: bool = False


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
    killing_source: str | None
    killing_origin_event_type: str | None
    total_overkill: float
    damage_by_source: tuple[CombatSimulationDamageSourceSummary, ...]
    unresolved: tuple[str, ...]
    damage_unresolved: tuple[str, ...]

    @property
    def complete_damage_evidence(self) -> bool:
        return not self.damage_unresolved

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

        if (
            result.target_state is not None
            and result.target_state.combatant(target) is None
        ):
            raise ValueError(
                f"combat simulation damage summary target is not present in target state: {target!r}"
            )

        outgoing = tuple(
            event
            for event in result.events
            if event.event_type == "outgoing_damage"
            and str(event.payload_dict().get("recipient") or "").strip() == target
        )
        summary_unresolved = list(result.unresolved)
        summary_damage_unresolved = list(result.damage_unresolved)
        if result.target_state is None and outgoing:
            summary_damage_unresolved.append(
                f"{target}: target Health state is required to prove applied outgoing damage"
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

        def finite_nonnegative(value) -> float | None:
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return None
            if not isfinite(numeric) or numeric < 0:
                return None
            return numeric

        source_totals: dict[str, list[float]] = {}
        for event in outgoing:
            payload = event.payload_dict()
            source = str(event.source or "unknown").strip() or "unknown"
            row = source_totals.setdefault(source, [0.0, 0.0, 0.0, 0.0])
            row[0] += 1.0
            attempted = finite_nonnegative(payload.get("amount"))
            if attempted is None:
                summary_damage_unresolved.append(
                    f"{source} outgoing_damage at {event.time_seconds:g}s -> {target}: "
                    "damage amount must be finite and non-negative"
                )
            else:
                row[1] += attempted

        outgoing_health = tuple(
            event
            for event in health
            if event.payload_dict().get("origin_event_type") == "outgoing_damage"
        )
        def damage_coordinate(event) -> tuple[float, str, str]:
            payload = event.payload_dict()
            return (
                float(event.time_seconds),
                str(event.source or "").strip(),
                str(payload.get("recipient") or "").strip(),
            )

        outgoing_sequences_by_coordinate: dict[
            tuple[float, str, str],
            set[int],
        ] = {}
        for event in outgoing:
            outgoing_sequences_by_coordinate.setdefault(
                damage_coordinate(event),
                set(),
            ).add(int(event.sequence))

        outgoing_health_count_by_coordinate: dict[
            tuple[float, str, str],
            int,
        ] = {}
        for event in outgoing_health:
            coordinate = damage_coordinate(event)
            outgoing_health_count_by_coordinate[coordinate] = (
                outgoing_health_count_by_coordinate.get(coordinate, 0) + 1
            )

        all_damage_coordinates = (
            set(outgoing_sequences_by_coordinate)
            | set(outgoing_health_count_by_coordinate)
        )
        for coordinate in sorted(all_damage_coordinates):
            time_seconds, source, recipient = coordinate
            expected_transitions = len(
                outgoing_sequences_by_coordinate.get(coordinate, set())
            )
            actual_transitions = outgoing_health_count_by_coordinate.get(
                coordinate,
                0,
            )
            if actual_transitions < expected_transitions:
                summary_damage_unresolved.append(
                    f"{source or 'unknown'} outgoing_damage at {time_seconds:g}s "
                    f"-> {recipient}: matching Health transition is unavailable"
                )
            elif actual_transitions > expected_transitions:
                summary_damage_unresolved.append(
                    f"{source or 'unknown'} health_change at {time_seconds:g}s "
                    f"-> {recipient}: matching raw outgoing damage is unavailable"
                )
        for event in outgoing_health:
            payload = event.payload_dict()
            source = str(event.source or "unknown").strip() or "unknown"
            row = source_totals.setdefault(source, [0.0, 0.0, 0.0, 0.0])
            applied = finite_nonnegative(payload.get("applied_damage"))
            if applied is None:
                summary_damage_unresolved.append(
                    f"{source} health_change at {event.time_seconds:g}s -> {target}: "
                    "applied outgoing damage is unavailable or invalid"
                )
            else:
                row[2] += applied
            overkill = finite_nonnegative(payload.get("overkill"))
            if overkill is None:
                summary_damage_unresolved.append(
                    f"{source} health_change at {event.time_seconds:g}s -> {target}: "
                    "outgoing damage overkill is unavailable or invalid"
                )
            else:
                row[3] += overkill

        outgoing_deaths = tuple(
            event
            for event in deaths
            if event.payload_dict().get("origin_event_type") == "outgoing_damage"
        )
        lethal_outgoing_health = tuple(
            event
            for event in outgoing_health
            if int(event.payload_dict().get("after") or 0) == 0
        )
        if lethal_outgoing_health and not outgoing_deaths:
            lethal = lethal_outgoing_health[0]
            summary_unresolved.append(
                f"{lethal.source} lethal outgoing damage at {lethal.time_seconds:g}s "
                f"-> {target}: death attribution event is unavailable"
            )
        killing_event = (
            min(
                outgoing_deaths,
                key=lambda event: (
                    float(event.time_seconds),
                    int(event.priority),
                    int(event.sequence),
                    str(event.source or "").casefold(),
                ),
            )
            if outgoing_deaths
            else None
        )
        killing_source = (
            str(killing_event.source or "").strip() or "unknown"
            if killing_event is not None
            else None
        )
        killing_origin_event_type = (
            str(killing_event.payload_dict().get("origin_event_type") or "").strip()
            or None
            if killing_event is not None
            else None
        )

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
            attempted_damage=sum(values[1] for values in source_totals.values()),
            applied_damage=sum(values[2] for values in source_totals.values()),
            ending_target_health=ending,
            target_maximum_health=maximum,
            target_dead=bool(deaths) or ending == 0,
            death_time_seconds=(
                float(killing_event.time_seconds)
                if killing_event is not None
                else None
            ),
            killing_source=killing_source,
            killing_origin_event_type=killing_origin_event_type,
            total_overkill=sum(values[3] for values in source_totals.values()),
            damage_by_source=tuple(
                CombatSimulationDamageSourceSummary(
                    source=source,
                    event_count=int(values[0]),
                    attempted_damage=float(values[1]),
                    applied_damage=float(values[2]),
                    overkill=float(values[3]),
                    killing_blow=(source == killing_source),
                )
                for source, values in sorted(
                    source_totals.items(),
                    key=lambda item: (-item[1][2], -item[1][1], item[0].casefold()),
                )
            ),
            unresolved=tuple(dict.fromkeys(summary_unresolved)),
            damage_unresolved=tuple(dict.fromkeys(summary_damage_unresolved)),
        )


__all__ = [
    "CombatSimulationDamageSourceSummary",
    "CombatSimulationDamageSummary",
    "CombatSimulationDamageSummaryService",
]
