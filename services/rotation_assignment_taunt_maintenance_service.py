from __future__ import annotations

"""Translate explicit provider ownership into continuous tank taunt maintenance.

Provider assignment proves *who* owns the encounter responsibility. This policy
layer proves the source-backed taunt skill, exact planning target, and reviewed
clock window that must remain continuously taunted. Canonical duration remains
owned by RotationTankTauntDurationService and refresh strategy remains a separate
caller-owned policy.
"""

from dataclasses import dataclass
import math

from minmax.character_build.character_build import CharacterBuild
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
)


@dataclass(frozen=True)
class RotationAssignmentTauntMaintenanceWindow:
    occurrence_id: str
    target_key: str
    active_start_seconds: float
    active_end_seconds: float
    bar: str | None = None

    def __post_init__(self) -> None:
        occurrence_id = str(self.occurrence_id or "").strip()
        target_key = str(self.target_key or "").strip()
        if not occurrence_id:
            raise ValueError("rotation assignment taunt maintenance occurrence_id is required")
        if not target_key:
            raise ValueError("rotation assignment taunt maintenance target_key is required")
        object.__setattr__(self, "occurrence_id", occurrence_id)
        object.__setattr__(self, "target_key", target_key)

        start = float(self.active_start_seconds)
        end = float(self.active_end_seconds)
        if not math.isfinite(start) or start < 0:
            raise ValueError("rotation assignment taunt maintenance start must be finite and non-negative")
        if not math.isfinite(end) or end <= start:
            raise ValueError("rotation assignment taunt maintenance end must be finite and greater than start")
        object.__setattr__(self, "active_start_seconds", start)
        object.__setattr__(self, "active_end_seconds", end)

        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("rotation assignment taunt maintenance bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationAssignmentTauntMaintenancePolicy:
    requirement_id: str
    encounter_id: str
    requirement_type: str
    source_skill_name: str
    windows: tuple[RotationAssignmentTauntMaintenanceWindow, ...]
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
                    f"rotation assignment taunt maintenance policy {field_name} must be non-empty"
                )
            object.__setattr__(self, field_name, value)

        windows = tuple(self.windows)
        if not windows:
            raise ValueError("rotation assignment taunt maintenance policy requires at least one window")
        seen: set[str] = set()
        for window in windows:
            if window.occurrence_id in seen:
                raise ValueError(
                    "duplicate rotation assignment taunt maintenance occurrence_id: "
                    f"{window.occurrence_id}"
                )
            seen.add(window.occurrence_id)
        object.__setattr__(self, "windows", windows)


@dataclass(frozen=True)
class RotationDerivedTauntMaintenanceObligation:
    assignment: ProviderAssignment
    policy: RotationAssignmentTauntMaintenancePolicy
    requirement: RotationTankTauntMaintenanceRequirement


@dataclass(frozen=True)
class RotationAssignmentTauntMaintenanceProjection:
    member_id: str
    character_name: str | None
    build_name: str
    role: str
    obligations: tuple[RotationDerivedTauntMaintenanceObligation, ...]

    @property
    def requirements(self) -> tuple[RotationTankTauntMaintenanceRequirement, ...]:
        return tuple(item.requirement for item in self.obligations)


class RotationAssignmentTauntMaintenanceService:
    """Derive continuous target-specific taunt ownership from provider assignment."""

    def derive(
        self,
        *,
        build: CharacterBuild,
        member_id: str,
        assignments: tuple[ProviderAssignment, ...],
        policies: tuple[RotationAssignmentTauntMaintenancePolicy, ...],
    ) -> RotationAssignmentTauntMaintenanceProjection:
        resolved_member_id = str(member_id or "").strip()
        if not resolved_member_id:
            raise ValueError("rotation assignment taunt maintenance requires member_id")

        assignment_by_id: dict[str, ProviderAssignment] = {}
        for assignment in assignments:
            key = assignment.requirement_id.casefold()
            if key in assignment_by_id:
                raise ValueError(
                    f"duplicate provider assignment requirement_id: {assignment.requirement_id!r}"
                )
            assignment_by_id[key] = assignment

        policy_by_id: dict[str, RotationAssignmentTauntMaintenancePolicy] = {}
        for policy in policies:
            key = policy.requirement_id.casefold()
            if key in policy_by_id:
                raise ValueError(
                    "duplicate rotation assignment taunt maintenance policy requirement_id: "
                    f"{policy.requirement_id!r}"
                )
            assignment = assignment_by_id.get(key)
            if assignment is None:
                raise ValueError(
                    "rotation assignment taunt maintenance policy references a requirement "
                    f"without a provider assignment: {policy.requirement_id!r}"
                )
            self._validate_policy_assignment(policy, assignment)
            policy_by_id[key] = policy

        obligations: list[RotationDerivedTauntMaintenanceObligation] = []
        for assignment in assignments:
            if assignment.status is not ProviderAssignmentStatus.ASSIGNED:
                continue

            primaries = tuple(
                provider
                for provider in assignment.primary_providers
                if provider.member_id == resolved_member_id
            )
            if not primaries:
                continue
            if len(primaries) > 1:
                raise ValueError(
                    "provider assignment contains duplicate primary provider identity for "
                    f"member {resolved_member_id!r} and requirement {assignment.requirement_id!r}"
                )

            policy = policy_by_id.get(assignment.requirement_id.casefold())
            if policy is None:
                continue

            provider = primaries[0]
            self._validate_provider_build(provider, build)
            for window in policy.windows:
                requirement = RotationTankTauntMaintenanceRequirement(
                    requirement_id=f"{policy.requirement_id}:{window.occurrence_id}",
                    source_skill_name=policy.source_skill_name,
                    target_key=window.target_key,
                    active_start_seconds=window.active_start_seconds,
                    active_end_seconds=window.active_end_seconds,
                    bar=window.bar,
                    provenance=(
                        f"assignment={assignment.requirement_id}",
                        f"encounter={assignment.encounter_id}",
                        f"source={policy.source}",
                    ),
                )
                obligations.append(
                    RotationDerivedTauntMaintenanceObligation(
                        assignment=assignment,
                        policy=policy,
                        requirement=requirement,
                    )
                )

        return RotationAssignmentTauntMaintenanceProjection(
            member_id=resolved_member_id,
            character_name=build.character_name,
            build_name=build.name,
            role=build.role.value,
            obligations=tuple(obligations),
        )

    @staticmethod
    def _validate_policy_assignment(
        policy: RotationAssignmentTauntMaintenancePolicy,
        assignment: ProviderAssignment,
    ) -> None:
        if policy.encounter_id != assignment.encounter_id:
            raise ValueError(
                "rotation taunt maintenance policy encounter_id does not match assignment for "
                f"{policy.requirement_id!r}"
            )
        if policy.requirement_type != assignment.requirement_type:
            raise ValueError(
                "rotation taunt maintenance policy requirement_type does not match assignment for "
                f"{policy.requirement_id!r}"
            )

    @staticmethod
    def _validate_provider_build(provider, build: CharacterBuild) -> None:
        if provider.build_name and provider.build_name != build.name:
            raise ValueError(
                "assigned taunt-maintenance provider build does not match Rotation Maker build: "
                f"assignment={provider.build_name!r}, build={build.name!r}"
            )
        if (
            build.character_name
            and provider.character_name
            and provider.character_name != build.character_name
        ):
            raise ValueError(
                "assigned taunt-maintenance provider character does not match Rotation Maker build: "
                f"assignment={provider.character_name!r}, build={build.character_name!r}"
            )


__all__ = [
    "RotationAssignmentTauntMaintenancePolicy",
    "RotationAssignmentTauntMaintenanceProjection",
    "RotationAssignmentTauntMaintenanceService",
    "RotationAssignmentTauntMaintenanceWindow",
    "RotationDerivedTauntMaintenanceObligation",
]
