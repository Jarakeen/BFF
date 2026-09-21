from __future__ import annotations

"""Project the actually executed RotationPlan when combat ends early."""

from minmax.rotation_plan import RotationPlan


class CombatSimulationFightTerminationService:
    """Truncate a plan at an exact terminal action ordering point.

    The original RotationPlan remains immutable planning truth. This service creates
    an execution projection only, so resource/healing/effect consequence services see
    the same shortened fight horizon as damage.
    """

    def truncate(
        self,
        plan: RotationPlan,
        *,
        time_seconds: float,
        sequence: int,
        reason: str = "target defeated",
    ) -> RotationPlan:
        terminal_time = float(time_seconds)
        terminal_sequence = int(sequence)
        if terminal_time < 0.0:
            raise ValueError("combat simulation termination time cannot be negative")
        if terminal_time > plan.duration_seconds:
            raise ValueError("combat simulation termination cannot exceed plan duration")
        if terminal_sequence < 0:
            raise ValueError("combat simulation termination sequence cannot be negative")

        actions = tuple(
            action
            for action in plan.actions
            if (
                action.time_seconds < terminal_time
                or (
                    action.time_seconds == terminal_time
                    and action.sequence <= terminal_sequence
                )
            )
        )
        note = (
            f"Combat Simulation execution ended at {terminal_time:g}s "
            f"sequence {terminal_sequence}: {str(reason or 'target defeated').strip()}"
        )
        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=terminal_time,
            actions=actions,
            assumptions=tuple(dict.fromkeys((*plan.assumptions, note))),
            unresolved=plan.unresolved,
        )


__all__ = ["CombatSimulationFightTerminationService"]
