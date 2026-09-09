from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from services.team_provider_rotation_workload_service import TeamProviderRotationWorkload
from services.team_provider_workload_decision_service import (
    TeamProviderWorkloadDecision,
    TeamProviderWorkloadDecisionResult,
    TeamProviderWorkloadDecisionStatus,
)


_EPSILON = 1e-9


def _canonical(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


class TeamProviderWorkloadPolicyDimension(str, Enum):
    PROVIDER_APPLICATIONS = "provider_applications"
    PROVIDER_GCD_SECONDS = "provider_gcd_seconds"
    PROVIDER_CAST_CHANNEL_SECONDS = "provider_cast_channel_seconds"
    ULTIMATE_SPENT = "ultimate_spent"
    OCCUPIED_BAR_SLOTS = "occupied_bar_slots"
    PRIMARY_ROLE_DISPLACEMENT_SECONDS = "primary_role_displacement_seconds"
    RESOURCE_SPEND = "resource_spend"


@dataclass(frozen=True)
class TeamProviderWorkloadPolicyPriority:
    dimension: TeamProviderWorkloadPolicyDimension
    resource_type: str | None = None

    def __post_init__(self) -> None:
        resource = _canonical(self.resource_type)
        if self.dimension is TeamProviderWorkloadPolicyDimension.RESOURCE_SPEND:
            if not resource:
                raise ValueError("resource-spend policy priority requires resource_type")
            object.__setattr__(self, "resource_type", resource)
        elif resource:
            raise ValueError(
                "resource_type is only valid for the resource-spend policy dimension"
            )
        else:
            object.__setattr__(self, "resource_type", None)

    @property
    def key(self) -> str:
        if self.dimension is TeamProviderWorkloadPolicyDimension.RESOURCE_SPEND:
            return f"resource_spend:{self.resource_type}"
        return self.dimension.value


@dataclass(frozen=True)
class TeamProviderWorkloadPolicy:
    policy_id: str
    priorities: tuple[TeamProviderWorkloadPolicyPriority, ...]
    encounter_key: str | None = None
    role_key: str | None = None

    def __post_init__(self) -> None:
        policy_id = str(self.policy_id or "").strip()
        if not policy_id:
            raise ValueError("provider workload policy_id is required")
        if not self.priorities:
            raise ValueError("provider workload policy requires at least one priority")

        seen: set[str] = set()
        for priority in self.priorities:
            if priority.key in seen:
                raise ValueError(f"duplicate provider workload policy priority: {priority.key}")
            seen.add(priority.key)

        object.__setattr__(self, "policy_id", policy_id)
        encounter = _canonical(self.encounter_key)
        role = _canonical(self.role_key)
        object.__setattr__(self, "encounter_key", encounter or None)
        object.__setattr__(self, "role_key", role or None)


@dataclass(frozen=True)
class TeamProviderWorkloadPolicySelection:
    effect_key: str
    duration_seconds: float
    preferred_ids: tuple[str, ...]
    considered_ids: tuple[str, ...]
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class TeamProviderWorkloadPolicyResult:
    policy: TeamProviderWorkloadPolicy
    selections: tuple[TeamProviderWorkloadPolicySelection, ...]

    @property
    def preferred_ids(self) -> tuple[str, ...]:
        return tuple(
            alternative_id
            for selection in self.selections
            for alternative_id in selection.preferred_ids
        )


class TeamProviderWorkloadPolicyService:
    """Apply explicit encounter/role priorities to non-dominated provider plans.

    The frontier remains the mathematical safety boundary. Policy is allowed to choose
    among frontier survivors only. Priorities are applied lexicographically in caller-
    supplied order rather than collapsed into a weighted score, so the result preserves
    the declared encounter/role preference instead of inventing exchange rates between
    healer time, Ultimate, Magicka, casts, or bar space.
    """

    @classmethod
    def select(
        cls,
        decisions: TeamProviderWorkloadDecisionResult,
        policy: TeamProviderWorkloadPolicy,
    ) -> TeamProviderWorkloadPolicyResult:
        groups: dict[tuple[str, float], list[TeamProviderWorkloadDecision]] = {}
        for decision in decisions.decisions:
            if decision.status is not TeamProviderWorkloadDecisionStatus.FRONTIER:
                continue
            if decision.workload is None or decision.duration_seconds is None:
                raise ValueError("frontier provider decision requires workload evidence")
            groups.setdefault(
                (decision.effect_key, float(decision.duration_seconds)), []
            ).append(decision)

        selections = tuple(
            cls._select_group(
                effect_key=effect_key,
                duration_seconds=duration_seconds,
                candidates=tuple(groups[(effect_key, duration_seconds)]),
                policy=policy,
            )
            for effect_key, duration_seconds in sorted(groups)
        )
        return TeamProviderWorkloadPolicyResult(policy=policy, selections=selections)

    @classmethod
    def _select_group(
        cls,
        *,
        effect_key: str,
        duration_seconds: float,
        candidates: tuple[TeamProviderWorkloadDecision, ...],
        policy: TeamProviderWorkloadPolicy,
    ) -> TeamProviderWorkloadPolicySelection:
        remaining = list(candidates)
        considered_ids = tuple(item.alternative_id for item in candidates)
        rationale: list[str] = []

        for priority in policy.priorities:
            if len(remaining) <= 1:
                break

            values = tuple(
                (item, cls._priority_value(item.workload, priority))
                for item in remaining
            )
            best = min(value for _, value in values)
            kept = [item for item, value in values if abs(value - best) <= _EPSILON]
            removed = [
                (item.alternative_id, value)
                for item, value in values
                if value > best + _EPSILON
            ]
            if removed:
                kept_ids = ", ".join(item.alternative_id for item in kept)
                removed_text = ", ".join(
                    f"{alternative_id}={value:g}" for alternative_id, value in removed
                )
                rationale.append(
                    f"{priority.key}: kept {kept_ids} at {best:g}; "
                    f"deprioritized {removed_text}"
                )
            remaining = kept

        return TeamProviderWorkloadPolicySelection(
            effect_key=effect_key,
            duration_seconds=duration_seconds,
            preferred_ids=tuple(item.alternative_id for item in remaining),
            considered_ids=considered_ids,
            rationale=tuple(rationale),
        )

    @staticmethod
    def _priority_value(
        workload: TeamProviderRotationWorkload | None,
        priority: TeamProviderWorkloadPolicyPriority,
    ) -> float:
        if workload is None:
            raise ValueError("provider workload policy requires workload evidence")

        dimension = priority.dimension
        if dimension is TeamProviderWorkloadPolicyDimension.PROVIDER_APPLICATIONS:
            value = float(workload.provider_applications)
        elif dimension is TeamProviderWorkloadPolicyDimension.PROVIDER_GCD_SECONDS:
            value = workload.provider_gcd_seconds
        elif dimension is TeamProviderWorkloadPolicyDimension.PROVIDER_CAST_CHANNEL_SECONDS:
            value = workload.provider_cast_channel_seconds
        elif dimension is TeamProviderWorkloadPolicyDimension.ULTIMATE_SPENT:
            value = workload.ultimate_spent
        elif dimension is TeamProviderWorkloadPolicyDimension.OCCUPIED_BAR_SLOTS:
            value = float(workload.occupied_bar_slot_count)
        elif dimension is TeamProviderWorkloadPolicyDimension.PRIMARY_ROLE_DISPLACEMENT_SECONDS:
            value = workload.primary_role_displacement_seconds
        elif dimension is TeamProviderWorkloadPolicyDimension.RESOURCE_SPEND:
            value = dict(workload.resource_costs).get(priority.resource_type or "", 0.0)
        else:
            raise ValueError(f"unsupported provider workload policy dimension: {dimension}")

        value = float(value)
        if not isfinite(value) or value < 0:
            raise ValueError("provider workload policy values must be finite and non-negative")
        return value


__all__ = [
    "TeamProviderWorkloadPolicy",
    "TeamProviderWorkloadPolicyDimension",
    "TeamProviderWorkloadPolicyPriority",
    "TeamProviderWorkloadPolicyResult",
    "TeamProviderWorkloadPolicySelection",
    "TeamProviderWorkloadPolicyService",
]
