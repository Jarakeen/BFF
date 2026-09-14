from __future__ import annotations

"""Translate explicit encounter assignments into tank taunt-application obligations.

Provider assignment proves ownership. This policy layer proves only which canonical
taunt source skill must be applied, on which bar when specified, to which explicit
planning target when specified, and inside which explicit occurrence windows. It
deliberately does not infer taunt duration, refresh cadence, overtaunt/immunity
behavior, or continuous maintenance.
"""

from dataclasses import dataclass
import math

from minmax.character_build.character_build import CharacterBuild
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
)


@dataclass(frozen=True)
class RotationAssignmentTauntApplicationWindow:
    occurrence_id: str
    window_start_seconds: float
    window_end_seconds: float
    minimum_applications: int = 1
    bar: str | None = None
    target_key: str | None = None

    def __post_init__(self) -> None:
        occurrence_id = str(self.occurrence_id or "").strip()
        if not occurrence_id:
            raise ValueError("rotation assignment taunt window occurrence_id is required")
        object.__setattr__(self, "occurrence_id", occurrence_id)

        start = float(self.window_start_seconds)
        end = float(self.window_end_seconds)
        if not math.isfinite(start) or start < 0:
            raise ValueError("rotation assignment taunt window start must be finite and non-negative")
        if not math.isfinite(end) or end < start:
            raise ValueError("rotation assignment taunt window end must be finite and >= start")
        object.__setattr__(self, "window_start_seconds", start)
        object.__setattr__(self, "window_end_seconds", end)

        minimum = int(self.minimum_applications)
        if minimum < 1:
            raise ValueError("rotation assignment taunt minimum_applications must be positive")
        object.__setattr__(self, "minimum_applications", minimum)

        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("rotation assignment taunt window bar must be front or back")
            object.__setattr__(self, "bar", bar)

        if self.target_key is not None:
            target_key = str(self.target_key or "").strip()
            if not target_key:
                raise ValueError("rotation assignment taunt window target_key must be non-empty when supplied")
            object.__setattr__(self, "target_key", target_key)


@dataclass(frozen=True)
class RotationAssignmentTauntPolicy:
    """Verified non-duration taunt semantics for one exact provider assignment."""

    requirement_id: str
    encounter_id: str
    requirement_type: str
    source_skill_name: str
    windows: tuple[RotationAssignmentTauntApplicationWindow, ...]
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
                raise ValueError(f"rotation assignment taunt policy {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)

        windows = tuple(self.windows)
        if not windows:
            raise ValueError("rotation assignment taunt policy requires at least one application window")
        seen: set[str] = set()
        for window in windows:
            if window.occurrence_id in seen:
                raise ValueError(
                    f"duplicate rotation assignment taunt occurrence_id: {window.occurrence_id}"
                )
            seen.add(window.occurrence_id)
        object.__setattr__(self, "windows", windows)


@dataclass(frozen=True)
class RotationDerivedTauntApplicationObligation:
    assignment: ProviderAssignment
    policy: RotationAssignmentTauntPolicy
    requirement: RotationTankTauntApplicationRequirement


@dataclass(frozen=True)
class RotationAssignmentTauntObligationProjection:
    member_id: str
    character_name: str | None
    build_name: str
    role: str
    obligations: tuple[RotationDerivedTauntApplicationObligation, ...]

    @property
    def requirements(self) -> tuple[RotationTankTauntApplicationRequirement, ...]:
        return tuple(item.requirement for item in self.obligations)


class RotationAssignmentTauntObligationService:
    """Derive exact taunt-application obligations from assigned provider ownership."""

    def derive(
        self,
        *,
        build: CharacterBuild,
        member_id: str,
        assignments: tuple[ProviderAssignment, ...],
        policies: tuple[RotationAssignmentTauntPolicy, ...],
    ) -> RotationAssignmentTauntObligationProjection:
        resolved_member_id = str(member_id or "").strip()
        if not resolved_member_id:
            raise ValueError("rotation assignment taunt obligations require member_id")

        assignment_by_id: dict[str, ProviderAssignment] = {}
        for assignment in assignments:
            key = assignment.requirement_id.casefold()
            if key in assignment_by_id:
                raise ValueError(
                    f"duplicate provider assignment requirement_id: {assignment.requirement_id!r}"
                )
            assignment_by_id[key] = assignment

        policy_by_id: dict[str, RotationAssignmentTauntPolicy] = {}
        for policy in policies:
            key = policy.requirement_id.casefold()
            if key in policy_by_id:
                raise ValueError(
                    f"duplicate rotation assignment taunt policy requirement_id: {policy.requirement_id!r}"
                )
            assignment = assignment_by_id.get(key)
            if assignment is None:
                raise ValueError(
                    "rotation assignment taunt policy references a requirement without a provider assignment: "
                    f"{policy.requirement_id!r}"
                )
            self._validate_policy_assignment(policy, assignment)
            policy_by_id[key] = policy

        obligations: list[RotationDerivedTauntApplicationObligation] = []
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
                requirement = RotationTankTauntApplicationRequirement(
                    requirement_id=f"{policy.requirement_id}:{window.occurrence_id}",
                    source_skill_name=policy.source_skill_name,
                    window_start_seconds=window.window_start_seconds,
                    window_end_seconds=window.window_end_seconds,
                    minimum_applications=window.minimum_applications,
                    bar=window.bar,
                    target_key=window.target_key,
                    provenance=(
                        f"assignment={assignment.requirement_id}",
                        f"encounter={assignment.encounter_id}",
                        f"source={policy.source}",
                    ),
                )
                obligations.append(
                    RotationDerivedTauntApplicationObligation(
                        assignment=assignment,
                        policy=policy,
                        requirement=requirement,
                    )
                )

        return RotationAssignmentTauntObligationProjection(
            member_id=resolved_member_id,
            character_name=build.character_name,
            build_name=build.name,
            role=build.role.value,
            obligations=tuple(obligations),
        )

    @staticmethod
    def _validate_policy_assignment(
        policy: RotationAssignmentTauntPolicy,
        assignment: ProviderAssignment,
    ) -> None:
        if policy.encounter_id != assignment.encounter_id:
            raise ValueError(
                f"rotation taunt policy encounter_id does not match assignment for {policy.requirement_id!r}"
            )
        if policy.requirement_type != assignment.requirement_type:
            raise ValueError(
                f"rotation taunt policy requirement_type does not match assignment for {policy.requirement_id!r}"
            )

    @staticmethod
    def _validate_provider_build(provider, build: CharacterBuild) -> None:
        if provider.build_name and provider.build_name != build.name:
            raise ValueError(
                "assigned taunt provider build does not match Rotation Maker build: "
                f"assignment={provider.build_name!r}, build={build.name!r}"
            )
        if (
            build.character_name
            and provider.character_name
            and provider.character_name != build.character_name
        ):
            raise ValueError(
                "assigned taunt provider character does not match Rotation Maker build: "
                f"assignment={provider.character_name!r}, build={build.character_name!r}"
            )


__all__ = [
    "RotationAssignmentTauntApplicationWindow",
    "RotationAssignmentTauntObligationProjection",
    "RotationAssignmentTauntObligationService",
    "RotationAssignmentTauntPolicy",
    "RotationDerivedTauntApplicationObligation",
]
