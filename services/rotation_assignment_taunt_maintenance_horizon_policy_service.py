from __future__ import annotations

"""Materialize reviewed symbolic taunt-maintenance policy from canonical encounter horizon.

Provider ownership and reviewed strategy policy remain separate from fight-duration
mechanics. This layer permits reviewed policy to say that continuous taunt ownership
lasts until the projected encounter end without persisting a brittle absolute second.
Only a resolved RotationTankEncounterHorizon may turn that symbolic endpoint into the
existing numeric RotationAssignmentTauntMaintenancePolicy consumed downstream.

A symbolic encounter policy may deliberately omit ``source_skill_name`` and bar. Those
are saved-build/provider facts, not encounter facts. Generate may bind the policy to an
exact canonical taunt skill/bar supplied by the selected provider scope. The materializer
fails closed if neither the reviewed policy nor provider evidence supplies a unique skill.
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
    windows: tuple[RotationAssignmentTauntMaintenanceHorizonWindow, ...]
    source: str
    source_skill_name: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "requirement_id",
            "encounter_id",
            "requirement_type",
            "source",
        ):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(
                    f"symbolic taunt maintenance policy {field_name} must be non-empty"
                )
            object.__setattr__(self, field_name, value)
        if self.source_skill_name is not None:
            source_skill_name = str(self.source_skill_name or "").strip()
            if not source_skill_name:
                raise ValueError(
                    "symbolic taunt maintenance policy source_skill_name must be non-empty when supplied"
                )
            object.__setattr__(self, "source_skill_name", source_skill_name)
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
        provider_source_skill_name: str | None = None,
        provider_source_bar: str | None = None,
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

        reviewed_skill = (
            None
            if policy.source_skill_name is None
            else str(policy.source_skill_name or "").strip()
        )
        provider_skill = str(provider_source_skill_name or "").strip() or None
        if reviewed_skill and provider_skill and reviewed_skill.casefold() != provider_skill.casefold():
            return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                policy=None,
                resolved=False,
                unresolved=(
                    f"{policy.requirement_id}: reviewed taunt skill {reviewed_skill!r} does not match canonical provider taunt {provider_skill!r}",
                ),
            )
        source_skill_name = reviewed_skill or provider_skill
        if not source_skill_name:
            return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                policy=None,
                resolved=False,
                unresolved=(
                    f"{policy.requirement_id}: symbolic taunt-maintenance policy has no exact canonical provider taunt skill",
                ),
            )

        provider_bar = str(provider_source_bar or "").strip().casefold() or None
        if provider_bar is not None and provider_bar not in {"front", "back"}:
            raise ValueError("provider_source_bar must be front or back when supplied")

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
            if window.bar and provider_bar and window.bar != provider_bar:
                return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                    policy=None,
                    resolved=False,
                    unresolved=(
                        f"{policy.requirement_id}:{window.occurrence_id}: reviewed taunt bar {window.bar!r} does not match canonical provider bar {provider_bar!r}",
                    ),
                )
            windows.append(
                RotationAssignmentTauntMaintenanceWindow(
                    occurrence_id=window.occurrence_id,
                    target_key=window.target_key,
                    active_start_seconds=window.active_start_seconds,
                    active_end_seconds=end,
                    bar=window.bar or provider_bar,
                )
            )

        materialized = RotationAssignmentTauntMaintenancePolicy(
            requirement_id=policy.requirement_id,
            encounter_id=policy.encounter_id,
            requirement_type=policy.requirement_type,
            source_skill_name=source_skill_name,
            windows=tuple(windows),
            source=policy.source,
        )
        return RotationAssignmentTauntMaintenanceHorizonMaterialization(
            policy=materialized,
            resolved=True,
            evidence=(
                *tuple(horizon.evidence),
                f"symbolic_endpoint=encounter_end:{end:g}",
                f"provider_taunt={source_skill_name}",
                *(() if provider_bar is None else (f"provider_taunt_bar={provider_bar}",)),
            ),
        )


__all__ = [
    "RotationAssignmentTauntMaintenanceHorizonMaterialization",
    "RotationAssignmentTauntMaintenanceHorizonPolicy",
    "RotationAssignmentTauntMaintenanceHorizonPolicyService",
    "RotationAssignmentTauntMaintenanceHorizonWindow",
]
