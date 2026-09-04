from __future__ import annotations

from dataclasses import dataclass

from .healer_demand_policy import HealerDemandPolicyAssessment
from .rotation_plan import RotationAction, RotationActionKind, RotationPlan
from .rotation_reserve_protection import (
    DiscretionaryRotationSpend,
    RotationReserveProtectionAnalysis,
    analyze_rotation_reserve_protection,
)
from .rotation_resource_reserve import RotationResourceReserveAssessment
from .resource_timeline import ResourceTimelineResult


@dataclass(frozen=True)
class HealerDiscretionaryAction:
    """One scheduled healer cast approved by demand policy for sacrifice."""

    action: RotationAction
    skill_name: str
    bar: str


@dataclass(frozen=True)
class HealerReserveProtectionBridgeResult:
    """Auditable bridge from healer policy classification to reserve analysis."""

    demand_assessment: HealerDemandPolicyAssessment
    discretionary_actions: tuple[HealerDiscretionaryAction, ...]
    reserve_analysis: RotationReserveProtectionAnalysis


def analyze_healer_reserve_protection(
    *,
    plan: RotationPlan,
    demand_assessment: HealerDemandPolicyAssessment,
    timeline: ResourceTimelineResult,
    reserve_assessment: RotationResourceReserveAssessment,
) -> HealerReserveProtectionBridgeResult:
    """Nominate policy-approved healer casts and analyze their reserve impact.

    Only scheduled skill casts that occur strictly before the demand window and
    explicitly identify the saved bar are eligible. The bridge matches those
    casts against the exact bar/name pairs classified as discretionary by the
    healer demand policy. It does not infer healer purpose from a skill name and
    it does not classify neutral or protected actions as expendable.
    """

    demand = demand_assessment.demand
    if reserve_assessment.demand != demand:
        raise ValueError("healer reserve bridge requires matching demand assessments")

    discretionary_keys = {
        (item.policy.bar, item.policy.skill_name)
        for item in demand_assessment.discretionary
    }
    protected_keys = {
        (item.policy.bar, item.policy.skill_name)
        for item in demand_assessment.protected
    }

    selected: list[HealerDiscretionaryAction] = []
    spends: list[DiscretionaryRotationSpend] = []

    for action in plan.actions:
        if action.kind is not RotationActionKind.SKILL:
            continue
        if action.time_seconds >= demand.start_seconds:
            continue
        if action.bar is None:
            raise ValueError(
                "healer reserve bridge requires explicit bar context for pre-demand skill casts: "
                f"{action.name} at {action.time_seconds:g}s"
            )

        key = (action.bar, action.name or "")
        if key in protected_keys:
            continue
        if key not in discretionary_keys:
            continue

        selected.append(
            HealerDiscretionaryAction(
                action=action,
                skill_name=action.name or "",
                bar=action.bar,
            )
        )
        spends.append(
            DiscretionaryRotationSpend(
                time_seconds=action.time_seconds,
                source=action.name or "",
            )
        )

    analysis = analyze_rotation_reserve_protection(
        timeline=timeline,
        reserve_assessment=reserve_assessment,
        discretionary_spends=tuple(spends),
    )

    return HealerReserveProtectionBridgeResult(
        demand_assessment=demand_assessment,
        discretionary_actions=tuple(selected),
        reserve_analysis=analysis,
    )
