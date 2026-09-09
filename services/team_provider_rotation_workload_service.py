from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_execution_burden_service import (
    RotationExecutionBurden,
    RotationExecutionBurdenService,
)


def _canonical(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


@dataclass(frozen=True)
class TeamProviderScheduledActionCost:
    """Reviewed workload evidence for one exact scheduled provider action.

    The timestamp and sequence bind the evidence to an immutable ``RotationPlan``
    action. Costs stay explicit because an effect application may be a normal skill,
    an Ultimate, or another supported action with very different opportunity cost.
    ``primary_role_displacement_seconds`` is caller-supplied evidence; this service
    does not guess how much healing, tanking, or damage the action displaced.
    """

    time_seconds: float
    sequence: int
    gcd_seconds: float | None
    resource_type: str | None = None
    resource_cost: float | None = None
    ultimate_cost: float | None = None
    primary_role_displacement_seconds: float | None = None

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("provider action time must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_seconds)
        if self.sequence < 0:
            raise ValueError("provider action sequence cannot be negative")

        for field_name in (
            "gcd_seconds",
            "resource_cost",
            "ultimate_cost",
            "primary_role_displacement_seconds",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            normalized = float(value)
            if not isfinite(normalized) or normalized < 0:
                raise ValueError(f"{field_name} must be finite and non-negative")
            object.__setattr__(self, field_name, normalized)

        resource_type = _canonical(self.resource_type)
        object.__setattr__(self, "resource_type", resource_type or None)
        if resource_type and self.resource_cost is None:
            raise ValueError("resource_cost is required when resource_type is supplied")
        if not resource_type and self.resource_cost is not None:
            raise ValueError("resource_type is required when resource_cost is supplied")
        if resource_type == "none" and self.resource_cost != 0.0:
            raise ValueError("resource_type='none' requires resource_cost=0")


@dataclass(frozen=True)
class TeamProviderRotationContribution:
    plan: RotationPlan
    provider_actions: tuple[TeamProviderScheduledActionCost, ...]


@dataclass(frozen=True)
class TeamProviderRotationWorkload:
    alternative_id: str
    effect_key: str
    duration_seconds: float
    recipient_coverage_met: bool
    temporal_coverage_met: bool
    contributor_count: int
    provider_applications: int
    provider_applications_per_minute: float
    provider_refreshes: int
    provider_gcd_seconds: float
    refreshes_per_minute: float
    resource_costs: tuple[tuple[str, float], ...]
    ultimate_spent: float
    occupied_bar_slots: tuple[str, ...]
    primary_role_displacement_seconds: float
    whole_plan_burden: RotationExecutionBurden
    unresolved: tuple[str, ...]

    @property
    def viable(self) -> bool:
        return (
            self.recipient_coverage_met
            and self.temporal_coverage_met
            and not self.unresolved
        )

    @property
    def occupied_bar_slot_count(self) -> int:
        return len(self.occupied_bar_slots)


@dataclass(frozen=True)
class TeamProviderRotationWorkloadComparison:
    baseline: TeamProviderRotationWorkload
    candidate: TeamProviderRotationWorkload
    provider_applications_delta: int
    provider_applications_per_minute_delta: float
    provider_refreshes_delta: int
    provider_gcd_seconds_delta: float
    refreshes_per_minute_delta: float
    resource_cost_deltas: tuple[tuple[str, float], ...]
    ultimate_spent_delta: float
    occupied_bar_slot_count_delta: int
    primary_role_displacement_seconds_delta: float
    total_actions_delta: int
    skill_casts_delta: int
    ultimate_casts_delta: int
    heavy_attacks_delta: int
    bar_swaps_delta: int


class TeamProviderRotationWorkloadService:
    """Compare viable provider plans without collapsing burden into one score.

    Recipient and temporal coverage are hard gates. Once both alternatives satisfy
    them, the result exposes independent workload dimensions so later policy can
    explain the tradeoff instead of asserting that, for example, one heavy attack
    is universally equivalent to one bar slot or one Ultimate cast.
    """

    def __init__(
        self,
        burden_service: RotationExecutionBurdenService | None = None,
    ) -> None:
        self.burden_service = burden_service or RotationExecutionBurdenService()

    def assess(
        self,
        *,
        alternative_id: str,
        effect_key: str,
        duration_seconds: float,
        recipient_coverage_met: bool,
        temporal_coverage_met: bool,
        contributions: tuple[TeamProviderRotationContribution, ...],
        unresolved: tuple[str, ...] = (),
    ) -> TeamProviderRotationWorkload:
        alternative = str(alternative_id or "").strip()
        effect = _canonical(effect_key)
        duration = float(duration_seconds)
        if not alternative:
            raise ValueError("provider workload alternative_id is required")
        if not effect:
            raise ValueError("provider workload effect_key is required")
        if not isfinite(duration) or duration <= 0:
            raise ValueError("provider workload duration_seconds must be positive")
        if not contributions:
            raise ValueError("provider workload requires at least one rotation contribution")

        issues = [str(item).strip() for item in unresolved if str(item).strip()]
        resource_totals: dict[str, float] = {}
        occupied_slots: set[str] = set()
        provider_applications = 0
        provider_refreshes = 0
        provider_gcd_seconds = 0.0
        ultimate_spent = 0.0
        primary_role_displacement_seconds = 0.0
        total_burdens: list[RotationExecutionBurden] = []

        for contribution in contributions:
            plan = contribution.plan
            if abs(float(plan.duration_seconds) - duration) > 1e-9:
                raise ValueError("all provider rotation plans must use the comparison duration")
            contributor = f"{plan.character_name} / {plan.build_name}"
            issues.extend(f"{contributor}: {item}" for item in plan.unresolved)
            total_burdens.append(self.burden_service.assess(plan))

            action_lookup = {
                (float(action.time_seconds), action.sequence): action
                for action in plan.actions
            }
            seen: set[tuple[float, int]] = set()
            valid_contribution_applications = 0
            for evidence in contribution.provider_actions:
                key = (float(evidence.time_seconds), evidence.sequence)
                if key in seen:
                    raise ValueError(
                        f"duplicate provider workload evidence for {contributor} at {key}"
                    )
                seen.add(key)
                action = action_lookup.get(key)
                if action is None:
                    issues.append(
                        f"{contributor}: provider action at {evidence.time_seconds:g}s "
                        f"sequence {evidence.sequence} is not in the rotation plan"
                    )
                    continue
                if action.kind not in {
                    RotationActionKind.SKILL,
                    RotationActionKind.ULTIMATE,
                }:
                    issues.append(
                        f"{contributor}: {action.kind.value} at {action.time_seconds:g}s "
                        "is not a supported provider cast"
                    )
                    continue

                provider_applications += 1
                valid_contribution_applications += 1
                action_label = action.name or action.kind.value
                if evidence.gcd_seconds is None:
                    issues.append(
                        f"{contributor}: {action_label} has unresolved GCD occupancy"
                    )
                else:
                    provider_gcd_seconds += evidence.gcd_seconds

                if evidence.resource_type is not None:
                    if evidence.resource_type != "none":
                        resource_totals[evidence.resource_type] = (
                            resource_totals.get(evidence.resource_type, 0.0)
                            + float(evidence.resource_cost or 0.0)
                        )
                elif action.kind is RotationActionKind.SKILL:
                    issues.append(
                        f"{contributor}: {action_label} has unresolved resource cost; "
                        "use resource_type='none' and resource_cost=0 for a reviewed free cast"
                    )

                if action.kind is RotationActionKind.ULTIMATE:
                    if evidence.ultimate_cost is None:
                        issues.append(
                            f"{contributor}: {action_label} has unresolved Ultimate cost"
                        )
                    else:
                        ultimate_spent += evidence.ultimate_cost
                elif evidence.ultimate_cost not in {None, 0.0}:
                    raise ValueError("non-Ultimate provider actions cannot spend Ultimate")

                if evidence.primary_role_displacement_seconds is None:
                    issues.append(
                        f"{contributor}: {action_label} has unresolved primary-role displacement"
                    )
                else:
                    primary_role_displacement_seconds += (
                        evidence.primary_role_displacement_seconds
                    )

                if action.bar is None:
                    issues.append(
                        f"{contributor}: {action_label} has unresolved bar-slot ownership"
                    )
                else:
                    occupied_slots.add(
                        f"{_canonical(plan.character_name)}:{action.bar}:{_canonical(action_label)}"
                    )
            provider_refreshes += max(0, valid_contribution_applications - 1)

        burden = self._combine_burdens(total_burdens)
        return TeamProviderRotationWorkload(
            alternative_id=alternative,
            effect_key=effect,
            duration_seconds=duration,
            recipient_coverage_met=bool(recipient_coverage_met),
            temporal_coverage_met=bool(temporal_coverage_met),
            contributor_count=len(contributions),
            provider_applications=provider_applications,
            provider_applications_per_minute=provider_applications * 60.0 / duration,
            provider_refreshes=provider_refreshes,
            provider_gcd_seconds=provider_gcd_seconds,
            refreshes_per_minute=provider_refreshes * 60.0 / duration,
            resource_costs=tuple(sorted(resource_totals.items())),
            ultimate_spent=ultimate_spent,
            occupied_bar_slots=tuple(sorted(occupied_slots)),
            primary_role_displacement_seconds=primary_role_displacement_seconds,
            whole_plan_burden=burden,
            unresolved=tuple(dict.fromkeys(issues)),
        )

    @staticmethod
    def compare(
        baseline: TeamProviderRotationWorkload,
        candidate: TeamProviderRotationWorkload,
    ) -> TeamProviderRotationWorkloadComparison:
        if baseline.effect_key != candidate.effect_key:
            raise ValueError("provider workload alternatives must cover the same effect")
        if abs(baseline.duration_seconds - candidate.duration_seconds) > 1e-9:
            raise ValueError("provider workload alternatives must use the same duration")
        if not baseline.viable or not candidate.viable:
            raise ValueError(
                "provider workload comparison requires two coverage-satisfying, resolved alternatives"
            )

        baseline_resources = dict(baseline.resource_costs)
        candidate_resources = dict(candidate.resource_costs)
        resource_keys = sorted(set(baseline_resources) | set(candidate_resources))
        resource_deltas = tuple(
            (
                resource,
                candidate_resources.get(resource, 0.0)
                - baseline_resources.get(resource, 0.0),
            )
            for resource in resource_keys
        )
        before = baseline.whole_plan_burden
        after = candidate.whole_plan_burden
        return TeamProviderRotationWorkloadComparison(
            baseline=baseline,
            candidate=candidate,
            provider_applications_delta=(
                candidate.provider_applications - baseline.provider_applications
            ),
            provider_applications_per_minute_delta=(
                candidate.provider_applications_per_minute
                - baseline.provider_applications_per_minute
            ),
            provider_refreshes_delta=(
                candidate.provider_refreshes - baseline.provider_refreshes
            ),
            provider_gcd_seconds_delta=(
                candidate.provider_gcd_seconds - baseline.provider_gcd_seconds
            ),
            refreshes_per_minute_delta=(
                candidate.refreshes_per_minute - baseline.refreshes_per_minute
            ),
            resource_cost_deltas=resource_deltas,
            ultimate_spent_delta=candidate.ultimate_spent - baseline.ultimate_spent,
            occupied_bar_slot_count_delta=(
                candidate.occupied_bar_slot_count - baseline.occupied_bar_slot_count
            ),
            primary_role_displacement_seconds_delta=(
                candidate.primary_role_displacement_seconds
                - baseline.primary_role_displacement_seconds
            ),
            total_actions_delta=after.total_actions - before.total_actions,
            skill_casts_delta=after.skill_casts - before.skill_casts,
            ultimate_casts_delta=after.ultimate_casts - before.ultimate_casts,
            heavy_attacks_delta=after.heavy_attacks - before.heavy_attacks,
            bar_swaps_delta=after.bar_swaps - before.bar_swaps,
        )

    @staticmethod
    def _combine_burdens(
        burdens: list[RotationExecutionBurden],
    ) -> RotationExecutionBurden:
        return RotationExecutionBurden(
            total_actions=sum(item.total_actions for item in burdens),
            skill_casts=sum(item.skill_casts for item in burdens),
            ultimate_casts=sum(item.ultimate_casts for item in burdens),
            light_attacks=sum(item.light_attacks for item in burdens),
            heavy_attacks=sum(item.heavy_attacks for item in burdens),
            potions=sum(item.potions for item in burdens),
            bar_swaps=sum(item.bar_swaps for item in burdens),
            waits=sum(item.waits for item in burdens),
        )
