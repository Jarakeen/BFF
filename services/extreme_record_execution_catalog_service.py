from __future__ import annotations

"""Map canonical Extreme Records onto shared execution families.

The canonical record catalog is the user-facing vocabulary.  This service does
not create one optimizer per record.  Instead it classifies every record by the
shared execution substrate that can own it today, so related objectives reuse the
same legal-character universe, candidate generation, and canonical math.
"""

from dataclasses import dataclass
from enum import Enum

from services.extreme_complete_optimization_service import COMPLETE_EXTREME_OBJECTIVES
from services.extreme_record_objective_catalog_service import (
    EXTREME_RECORD_OBJECTIVES,
    ExtremeRecordObjective,
)


class ExtremeRecordExecutionStatus(str, Enum):
    READY = "ready"
    SPECIALIZED = "specialized"
    PENDING = "pending"


@dataclass(frozen=True)
class ExtremeRecordExecutionDescriptor:
    objective: ExtremeRecordObjective
    status: ExtremeRecordExecutionStatus
    execution_family: str
    evidence: str

    @property
    def executable_in_static_lab(self) -> bool:
        return self.execution_family == "shared-static-stat" and self.status is ExtremeRecordExecutionStatus.READY


_STATIC_KEYS = frozenset(objective.key for objective in COMPLETE_EXTREME_OBJECTIVES)

_SPECIALIZED_FAMILIES = {
    "actual_heal": "actual-heal-event",
    "critical_heal": "actual-heal-event",
    "damage_shield": "single-event-output",
    "bash_damage": "single-event-output",
    "resource_sustain": "resource-timeline",
    "ultimate_generation": "resource-timeline",
    "movement_speed": "movement-state",
    "sprint_speed": "movement-state",
    "stealthed_movement_speed": "movement-state",
    "detection_radius_reduction": "stealth-state",
    "invisibility_duration": "stealth-runtime",
    "invisibility_uptime": "stealth-runtime",
}

_PENDING_FAMILIES: dict[str, str] = {
    "sustained_dps": "combat-simulation",
}


class ExtremeRecordExecutionCatalogService:
    """Return one authoritative execution disposition for all Extreme records."""

    @classmethod
    def descriptors(cls) -> tuple[ExtremeRecordExecutionDescriptor, ...]:
        rows: list[ExtremeRecordExecutionDescriptor] = []
        for objective in EXTREME_RECORD_OBJECTIVES:
            if objective.key in _STATIC_KEYS:
                rows.append(
                    ExtremeRecordExecutionDescriptor(
                        objective=objective,
                        status=ExtremeRecordExecutionStatus.READY,
                        execution_family="shared-static-stat",
                        evidence=(
                            "Reuses ExtremeCompleteOptimizationService and the shared canonical "
                            "character-state/stat pipeline."
                        ),
                    )
                )
                continue

            specialized = _SPECIALIZED_FAMILIES.get(objective.key)
            if specialized is not None:
                rows.append(
                    ExtremeRecordExecutionDescriptor(
                        objective=objective,
                        status=ExtremeRecordExecutionStatus.SPECIALIZED,
                        execution_family=specialized,
                        evidence=(
                            "Dedicated backend mechanics exist; UI routing/scenario inputs remain "
                            "separate from the shared static-stat runner."
                        ),
                    )
                )
                continue

            family = _PENDING_FAMILIES.get(objective.key, "unclassified")
            rows.append(
                ExtremeRecordExecutionDescriptor(
                    objective=objective,
                    status=ExtremeRecordExecutionStatus.PENDING,
                    execution_family=family,
                    evidence=(
                        "Canonical record is defined but its shared execution family is not yet "
                        "wired end-to-end in Extreme Build Lab."
                    ),
                )
            )

        if len(rows) != len(EXTREME_RECORD_OBJECTIVES):
            raise AssertionError("Extreme record execution catalog drifted from canonical objective catalog")
        if tuple(row.objective.key for row in rows) != tuple(
            objective.key for objective in EXTREME_RECORD_OBJECTIVES
        ):
            raise AssertionError("Extreme record execution catalog changed canonical objective ordering")
        if any(row.execution_family == "unclassified" for row in rows):
            raise AssertionError("Extreme record execution catalog contains an unclassified objective")
        return tuple(rows)

    @classmethod
    def descriptor(cls, key: str) -> ExtremeRecordExecutionDescriptor:
        normalized = str(key or "").strip().casefold()
        for row in cls.descriptors():
            if row.objective.key == normalized:
                return row
        raise ValueError(f"Unsupported Extreme Records objective: {key!r}")


__all__ = [
    "ExtremeRecordExecutionCatalogService",
    "ExtremeRecordExecutionDescriptor",
    "ExtremeRecordExecutionStatus",
]
