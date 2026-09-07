from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.character_build.character_build import CharacterBuild
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement


@dataclass(frozen=True)
class RotationAssignmentEffectPolicy:
    """Verified translation from one exact provider assignment to rotation uptime.

    ProviderAssignment establishes who owns an encounter responsibility. This
    policy supplies only the rotation-specific semantic bridge that assignment
    evidence does not contain: which cast-produced effect, source skill, bar, and
    minimum uptime express that responsibility on the timeline.

    Policies are keyed by exact requirement_id rather than fuzzy requirement
    names/types so Rotation Maker never guesses strategy from labels.
    """

    requirement_id: str
    encounter_id: str
    requirement_type: str
    effect_name: str
    source_skill_name: str
    minimum_uptime: float
    source: str
    bar: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "requirement_id",
            "encounter_id",
            "requirement_type",
            "effect_name",
            "source_skill_name",
            "source",
        ):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"rotation assignment effect policy {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)

        minimum = float(self.minimum_uptime)
        if not math.isfinite(minimum) or not 0.0 <= minimum <= 1.0:
            raise ValueError(
                "rotation assignment effect policy minimum_uptime must be finite and between 0 and 1"
            )
        object.__setattr__(self, "minimum_uptime", minimum)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("rotation assignment effect policy bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationDerivedEffectObligation:
    """One assignment-backed runtime effect requirement with provenance."""

    assignment: ProviderAssignment
    policy: RotationAssignmentEffectPolicy
    requirement: RotationEffectUptimeRequirement


@dataclass(frozen=True)
class RotationAssignmentEffectObligationProjection:
    """Effect obligations owned by one exact build/member assignment."""

    member_id: str
    character_name: str | None
    build_name: str
    role: str
    obligations: tuple[RotationDerivedEffectObligation, ...]

    @property
    def requirements(self) -> tuple[RotationEffectUptimeRequirement, ...]:
        return tuple(item.requirement for item in self.obligations)


class RotationAssignmentEffectObligationService:
    """Derive runtime effect obligations from explicit provider ownership.

    Assignment evidence decides ownership; explicit RotationAssignmentEffectPolicy
    rows decide how that ownership translates to effect uptime. The service never
    infers an effect or source skill from requirement names and never assigns work
    based on role convention. This matters for support DDs and encounter-specific
    off-role responsibilities.
    """

    def derive(
        self,
        *,
        build: CharacterBuild,
        member_id: str,
        assignments: tuple[ProviderAssignment, ...],
        policies: tuple[RotationAssignmentEffectPolicy, ...],
    ) -> RotationAssignmentEffectObligationProjection:
        resolved_member_id = str(member_id or "").strip()
        if not resolved_member_id:
            raise ValueError("rotation assignment effect obligations require member_id")

        assignment_by_id: dict[str, ProviderAssignment] = {}
        for assignment in assignments:
            key = assignment.requirement_id.casefold()
            if key in assignment_by_id:
                raise ValueError(
                    f"duplicate provider assignment requirement_id: {assignment.requirement_id!r}"
                )
            assignment_by_id[key] = assignment

        policy_by_id: dict[str, RotationAssignmentEffectPolicy] = {}
        for policy in policies:
            key = policy.requirement_id.casefold()
            if key in policy_by_id:
                raise ValueError(
                    f"duplicate rotation assignment effect policy requirement_id: {policy.requirement_id!r}"
                )
            assignment = assignment_by_id.get(key)
            if assignment is None:
                raise ValueError(
                    "rotation assignment effect policy references a requirement without a provider assignment: "
                    f"{policy.requirement_id!r}"
                )
            self._validate_policy_assignment(policy, assignment)
            policy_by_id[key] = policy

        obligations: list[RotationDerivedEffectObligation] = []
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
                # Not every provider assignment is a timed cast-produced effect.
                # Absence from this explicit policy catalog means it is outside
                # this adapter's declared rotation-effect scope, not zero uptime.
                continue

            provider = primaries[0]
            self._validate_provider_build(provider, build)
            requirement = RotationEffectUptimeRequirement(
                effect_name=policy.effect_name,
                source_skill_name=policy.source_skill_name,
                minimum_uptime=policy.minimum_uptime,
                bar=policy.bar,
            )
            obligations.append(
                RotationDerivedEffectObligation(
                    assignment=assignment,
                    policy=policy,
                    requirement=requirement,
                )
            )

        return RotationAssignmentEffectObligationProjection(
            member_id=resolved_member_id,
            character_name=build.character_name,
            build_name=build.name,
            role=build.role.value,
            obligations=tuple(obligations),
        )

    @staticmethod
    def _validate_policy_assignment(
        policy: RotationAssignmentEffectPolicy,
        assignment: ProviderAssignment,
    ) -> None:
        if policy.encounter_id != assignment.encounter_id:
            raise ValueError(
                f"rotation effect policy encounter_id does not match assignment for {policy.requirement_id!r}"
            )
        if policy.requirement_type != assignment.requirement_type:
            raise ValueError(
                f"rotation effect policy requirement_type does not match assignment for {policy.requirement_id!r}"
            )

    @staticmethod
    def _validate_provider_build(provider, build: CharacterBuild) -> None:
        if provider.build_name and provider.build_name != build.name:
            raise ValueError(
                "assigned provider build does not match Rotation Maker build: "
                f"assignment={provider.build_name!r}, build={build.name!r}"
            )
        if (
            build.character_name
            and provider.character_name
            and provider.character_name != build.character_name
        ):
            raise ValueError(
                "assigned provider character does not match Rotation Maker build: "
                f"assignment={provider.character_name!r}, build={build.character_name!r}"
            )


__all__ = [
    "RotationAssignmentEffectObligationProjection",
    "RotationAssignmentEffectObligationService",
    "RotationAssignmentEffectPolicy",
    "RotationDerivedEffectObligation",
]
