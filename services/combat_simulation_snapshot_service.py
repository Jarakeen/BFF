from __future__ import annotations

"""Project exact-time snapshots from a deterministic Phase 14 simulation result."""

import math

from minmax.runtime_effect_window import partition_runtime_effect_windows
from models.combat_simulation import (
    CombatSimulationHealthSnapshot,
    CombatSimulationResourceSnapshot,
    CombatSimulationResult,
    CombatSimulationSnapshot,
)


class CombatSimulationSnapshotService:
    """Read exact current state from an already-computed simulation result.

    This service performs no ESO math. It only projects canonical simulation
    history into one exact-time view.
    """

    def snapshot_at(
        self,
        result: CombatSimulationResult,
        *,
        time_seconds: float,
        sequence: int | None = None,
    ) -> CombatSimulationSnapshot:
        instant = float(time_seconds)
        if not math.isfinite(instant) or instant < 0:
            raise ValueError("simulation snapshot time must be finite and non-negative")
        if instant > float(result.duration_seconds) + 1e-12:
            raise ValueError("simulation snapshot time cannot exceed simulation duration")
        boundary_sequence = None if sequence is None else int(sequence)
        if boundary_sequence is not None and boundary_sequence < 0:
            raise ValueError("simulation snapshot sequence cannot be negative")

        def visible(event) -> bool:
            if event.time_seconds < instant:
                return True
            if event.time_seconds > instant:
                return False
            return (
                boundary_sequence is None
                or int(event.sequence) <= boundary_sequence
            )

        active_bar = result.initial_bar
        for event in result.events:
            if event.time_seconds > instant:
                break
            if not visible(event):
                continue
            if event.event_type != "action":
                continue
            payload = event.payload_dict()
            if payload.get("kind") != "bar_swap":
                continue
            destination = str(payload.get("bar") or "").strip().casefold()
            if destination in {"front", "back"}:
                active_bar = destination

        resources = []
        for summary in result.resources:
            current = int(summary.starting_amount)
            for event in result.events:
                if event.time_seconds > instant:
                    break
                if not visible(event):
                    continue
                if event.event_type not in {
                    "action_cost",
                    "recovery_tick",
                    "restoration",
                    "resource_maximum",
                }:
                    continue
                payload = event.payload_dict()
                if payload.get("resource") != summary.resource:
                    continue
                if "after" in payload:
                    current = int(payload["after"])
            resources.append(
                CombatSimulationResourceSnapshot(
                    resource=summary.resource,
                    current_amount=current,
                )
            )

        health = []
        if result.target_state is not None:
            current_health = {
                item.identity: item.current_health
                for item in result.target_state.combatants
            }
            maximum_health = {
                item.identity: item.maximum_health
                for item in result.target_state.combatants
            }
            for event in result.events:
                if event.time_seconds > instant:
                    break
                if not visible(event):
                    continue
                if event.event_type != "health_change":
                    continue
                payload = event.payload_dict()
                recipient = str(payload.get("recipient") or "").strip()
                if recipient:
                    current_health[recipient] = int(payload["after"])
            health = [
                CombatSimulationHealthSnapshot(
                    identity=item.identity,
                    current_health=current_health.get(item.identity),
                    maximum_health=maximum_health.get(item.identity),
                    is_dead=(current_health.get(item.identity) == 0),
                )
                for item in result.target_state.combatants
            ]

        partition = partition_runtime_effect_windows(
            result.effect_windows,
            at_time_seconds=instant,
        )

        return CombatSimulationSnapshot(
            time_seconds=instant,
            active_bar=active_bar,
            resources=tuple(resources),
            health=tuple(health),
            active_effect_windows=partition.active,
            target_state=result.target_state,
            unresolved=tuple(result.unresolved),
        )


__all__ = ["CombatSimulationSnapshotService"]
