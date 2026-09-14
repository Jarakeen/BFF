from __future__ import annotations

"""Materialize reviewed symbolic taunt-maintenance policy from canonical encounter horizon.

Provider ownership and reviewed strategy policy remain separate from fight-duration
mechanics. This layer permits reviewed policy to say that continuous taunt ownership
lasts until the projected encounter end without persisting a brittle absolute second.
Only a resolved RotationTankEncounterHorizon may turn that symbolic endpoint into the
existing numeric RotationAssignmentTauntMaintenancePolicy consumed downstream.
"""

from dataclasses import dataclass
import math

from services.rotation_assignment_taunt_maintenance_service import (
    RotationAssignmentTauntMaintenancePolicy,
    RotationAssignmentTauntMaintenanceWindow,
)
from services.rotation_tank_encounter_horizon_service import RotationTankEncounterHorizon


@dataclass(frozen=True)
class RotationAssignmentTauntMaintenanceHorizonWindow:
    occurrence_id: str
    target_key: str
    active_start_seconds: float
    end_reference: str = "encounter_end"
    bar: str | None = None

    def __post_init__(self) -> None:
        occurrence_id = str(self.occurrence_id or "").strip()
        target_key = str(self.target_key or "").strip()
        end_reference = str(self.end_reference or "").strip().casefold()
        if not occurrence_id:
            raise ValueError("symbolic taunt maintenance occurrence_id is required")
        if not target_key:
            raise ValueError("symbolic taunt maintenance target_key is required")
        if end_reference != "encounter_end":
            raise ValueError(
                "symbolic taunt maintenance end_reference must be 'encounter_end'"
            )
        start = float(self.active_start_seconds)
        if not math.isfinite(start) or start < 0:
            raise ValueError(
                "symbolic taunt maintenance active_start_seconds must be finite and non-negative"
            )
        object.__setattr__(self, "occurrence_id", occurrence_id)
        object.__setattr__(self, "target_key", target_key)
        object.__setattr__(self, "end_reference", end_reference)
        object.__setattr__(self, "active_start_seconds", start)
        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("symbolic taunt maintenance bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationAssignmentTauntMaintenanceHorizonPolicy:
    requirement_id: str
    encounter_id: str
    requirement_type: str
    source_skill_name: str
    windows: tuple[RotationAssignmentTauntMaintenanceHorizonWindow, ...]
    source: str

    def __post_init__(self) -> None:
        for field_name in (
            "requirement_id",
            "encounter_id",
            "requirement_type",
            "source_skill_name",
            "source",
        ):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(
                    f"symbolic taunt maintenance policy {field_name} must be non-empty"
                )
            object.__setattr__(self, field_name, value)
        windows = tuple(self.windows)
        if not windows:
            raise ValueError(
                "symbolic taunt maintenance policy requires at least one window"
            )
        ids = [window.occurrence_id for window in windows]
        if len(ids) != len(set(ids)):
            raise ValueError(
                "symbolic taunt maintenance policy cannot duplicate occurrence_id"
            )
        object.__setattr__(self, "windows", windows)


@dataclass(frozen=True)
class RotationAssignmentTauntMaintenanceHorizonMaterialization:
    policy: RotationAssignmentTauntMaintenancePolicy | None
    resolved: bool
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class RotationAssignmentTauntMaintenanceHorizonPolicyService:
    """Resolve symbolic encounter-end windows into existing numeric maintenance policy."""

    def materialize(
        self,
        *,
        policy: RotationAssignmentTauntMaintenanceHorizonPolicy,
        horizon: RotationTankEncounterHorizon,
    ) -> RotationAssignmentTauntMaintenanceHorizonMaterialization:
        if horizon.encounter_id != policy.encounter_id:
            raise ValueError(
                "Tank encounter horizon does not match symbolic taunt maintenance policy encounter"
            )
        if not horizon.resolved or horizon.end_seconds is None:
            return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                policy=None,
                resolved=False,
                unresolved=tuple(horizon.unresolved)
                or ("Tank encounter horizon is unresolved",),
            )

        end = float(horizon.end_seconds)
        windows: list[RotationAssignmentTauntMaintenanceWindow] = []
        for window in policy.windows:
            if end <= window.active_start_seconds:
                return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                    policy=None,
                    resolved=False,
                    unresolved=(
                        f"{policy.requirement_id}:{window.occurrence_id}: projected encounter end "
                        "does not occur after the reviewed maintenance start",
                    ),
                )
            windows.append(
                RotationAssignmentTauntMaintenanceWindow(
                    occurrence_id=window.occurrence_id,
                    target_key=window.target_key,
                    active_start_seconds=window.active_start_seconds,
                    active_end_seconds=end,
                    bar=window.bar,
                )
            )

        materialized = RotationAssignmentTauntMaintenancePolicy(
            requirement_id=policy.requirement_id,
            encounter_id=policy.encounter_id,
            requirement_type=policy.requirement_type,
            source_skill_name=policy.source_skill_name,
            windows=tuple(windows),
            source=policy.source,
        )
        return RotationAssignmentTauntMaintenanceHorizonMaterialization(
            policy=materialized,
            resolved=True,
            evidence=(
                *tuple(horizon.evidence),
                f"symbolic_endpoint=encounter_end:{end:g}",
            ),
        )


__all__ = [
    "RotationAssignmentTauntMaintenanceHorizonMaterialization",
    "RotationAssignmentTauntMaintenanceHorizonPolicy",
    "RotationAssignmentTauntMaintenanceHorizonPolicyService",
    "RotationAssignmentTauntMaintenanceHorizonWindow",
]
