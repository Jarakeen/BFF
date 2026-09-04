from __future__ import annotations

from dataclasses import dataclass

from .healer_demand_policy import HealerDemandPolicyAssessment
from .healer_reserve_bridge import (
    HealerReserveProtectionBridgeResult,
    analyze_healer_reserve_protection,
)
from .healer_reserve_decision import (
    HealerReserveDecisionResult,
    propose_healer_reserve_decision_from_protection_plan,
)
from .resource_timeline import ResourceTimelineResult
from .rotation_budget_reserve_bridge import (
    RotationBudgetReserveBridgeResult,
    assess_budget_derived_reserve,
)
from .rotation_plan import RotationPlan
from .rotation_reserve_priority import ReserveProtectionPriority
from .rotation_reserve_replay import (
    ExactReserveProtectionPlan,
    ResourceTimelineReplayInputs,
    plan_exact_rotation_reserve_protection,
)
from .rotation_window_resource_budget import RotationWindowResourceBudget


@dataclass(frozen=True)
class HealerExactBudgetReserveDecisionResult:
    """Budget-derived healer reserve decision proven by exact timeline replay."""

    budget_reserve: RotationBudgetReserveBridgeResult
    healer_bridge: HealerReserveProtectionBridgeResult
    exact_protection: ExactReserveProtectionPlan
    decision: HealerReserveDecisionResult


def propose_healer_exact_budget_reserve_decision(
    *,
    plan: RotationPlan,
    demand_assessment: HealerDemandPolicyAssessment,
    timeline: ResourceTimelineResult,
    budget: RotationWindowResourceBudget,
    priorities: tuple[ReserveProtectionPriority, ...],
    replay_inputs: ResourceTimelineReplayInputs,
) -> HealerExactBudgetReserveDecisionResult:
    """Compose healer policy, budgeted reserve, exact replay, and adjustment.

    The supplied timeline establishes the original demand-entry state and policy
    candidates. Replay inputs must reproduce that state exactly; the generic
    exact planner enforces this before selecting any withholding prefix. The
    resulting replay-proven protection plan is applied directly to the healer
    schedule without falling back through arithmetic reserve selection.
    """

    budget_reserve = assess_budget_derived_reserve(
        timeline=timeline,
        demand=demand_assessment.demand,
        budget=budget,
    )
    healer_bridge = analyze_healer_reserve_protection(
        plan=plan,
        demand_assessment=demand_assessment,
        timeline=timeline,
        reserve_assessment=budget_reserve.assessment,
    )
    exact_protection = plan_exact_rotation_reserve_protection(
        analysis=healer_bridge.reserve_analysis,
        priorities=priorities,
        replay_inputs=replay_inputs,
    )
    decision = propose_healer_reserve_decision_from_protection_plan(
        plan=plan,
        bridge=healer_bridge,
        protection_plan=exact_protection.protection_plan,
    )

    return HealerExactBudgetReserveDecisionResult(
        budget_reserve=budget_reserve,
        healer_bridge=healer_bridge,
        exact_protection=exact_protection,
        decision=decision,
    )
