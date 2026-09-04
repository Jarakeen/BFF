from __future__ import annotations

from dataclasses import dataclass

from .healer_demand_policy import HealerDemandPolicyAssessment
from .healer_reserve_bridge import (
    HealerReserveProtectionBridgeResult,
    analyze_healer_reserve_protection,
)
from .healer_reserve_decision import (
    HealerReserveDecisionResult,
    propose_healer_reserve_decision,
)
from .resource_timeline import ResourceTimelineResult
from .rotation_budget_reserve_bridge import (
    RotationBudgetReserveBridgeResult,
    assess_budget_derived_reserve,
)
from .rotation_plan import RotationPlan
from .rotation_reserve_priority import ReserveProtectionPriority
from .rotation_window_resource_budget import RotationWindowResourceBudget


@dataclass(frozen=True)
class HealerBudgetReserveDecisionResult:
    """Healer reserve decision derived directly from a required-action budget.

    This composer removes the need for callers to manually construct a reserve
    requirement or reserve assessment. It preserves each intermediate result so
    the derived budget, healer-policy nomination, reserve analysis, and final
    schedule adjustment remain independently auditable.
    """

    budget_reserve: RotationBudgetReserveBridgeResult
    healer_bridge: HealerReserveProtectionBridgeResult
    decision: HealerReserveDecisionResult


def propose_healer_budget_reserve_decision(
    *,
    plan: RotationPlan,
    demand_assessment: HealerDemandPolicyAssessment,
    timeline: ResourceTimelineResult,
    budget: RotationWindowResourceBudget,
    priorities: tuple[ReserveProtectionPriority, ...],
) -> HealerBudgetReserveDecisionResult:
    """Compose budget-derived reserve assessment into one healer decision.

    The required-action budget owns the minimum resource needed at demand entry.
    The healer demand assessment owns which scheduled casts are protected,
    discretionary, or neutral. Generic reserve analysis and schedule adjustment
    remain delegated to their existing layers.
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
    decision = propose_healer_reserve_decision(
        plan=plan,
        bridge=healer_bridge,
        priorities=priorities,
    )

    return HealerBudgetReserveDecisionResult(
        budget_reserve=budget_reserve,
        healer_bridge=healer_bridge,
        decision=decision,
    )
