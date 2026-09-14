from __future__ import annotations

"""Resolve a Tank rotation encounter horizon from canonical damage-trajectory evidence."""

from dataclasses import dataclass

from minmax.fight_damage_trajectory import project_fight_end_time
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
)


@dataclass(frozen=True)
class RotationTankEncounterHorizon:
    encounter_id: str
    end_seconds: float | None
    resolved: bool
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class RotationTankEncounterHorizonService:
    """Expose the projected fight end without inventing a default Tank horizon."""

    def resolve(
        self,
        *,
        encounter_id: str,
        health_threshold_projection: EncounterHealthThresholdProjection | None,
    ) -> RotationTankEncounterHorizon:
        resolved_encounter = str(encounter_id or "").strip()
        if not resolved_encounter:
            raise ValueError("Tank encounter horizon requires encounter_id")

        projection = health_threshold_projection
        if projection is None:
            return RotationTankEncounterHorizon(
                encounter_id=resolved_encounter,
                end_seconds=None,
                resolved=False,
                unresolved=(
                    "canonical health/damage trajectory is unavailable for Tank encounter horizon",
                ),
            )
        if projection.encounter_id != resolved_encounter:
            raise ValueError(
                "Tank encounter horizon projection encounter_id does not match selected encounter"
            )
        if projection.trajectory is None:
            reason = tuple(projection.unresolved) or (
                "canonical fight-damage trajectory is unavailable",
            )
            return RotationTankEncounterHorizon(
                encounter_id=resolved_encounter,
                end_seconds=None,
                resolved=False,
                unresolved=reason,
            )

        end = project_fight_end_time(projection.trajectory)
        if not end.resolved or end.time_seconds is None:
            return RotationTankEncounterHorizon(
                encounter_id=resolved_encounter,
                end_seconds=None,
                resolved=False,
                unresolved=(end.reason,),
            )

        return RotationTankEncounterHorizon(
            encounter_id=resolved_encounter,
            end_seconds=float(end.time_seconds),
            resolved=True,
            evidence=(
                end.reason,
                f"difficulty={projection.difficulty}",
                f"maximum_health={projection.maximum_health}",
            ),
        )


__all__ = [
    "RotationTankEncounterHorizon",
    "RotationTankEncounterHorizonService",
]
