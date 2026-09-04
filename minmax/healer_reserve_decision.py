from __future__ import annotations

from dataclasses import dataclass

from .healer_reserve_bridge import HealerReserveProtectionBridgeResult
from .rotation_plan import RotationPlan
from .rotation_reserve_adjustment import (
    ReserveProtectionActionBinding,
    RotationReserveAdjustmentProposal,
    propose_rotation_reserve_adjustment,
)
from .rotation_reserve_priority import (
    ReserveProtectionPriority,
    RotationReserveProtectionPlan,
    plan_rotation_reserve_protection,
)


@dataclass(frozen=True)
class HealerReserveDecisionResult:
    """End-to-end healer reserve decision for one encounter demand window.

    The healer policy bridge owns which casts are discretionary. This layer owns
    only the explicit order in which those casts may be sacrificed and the exact
    binding back to scheduled actions. Resource math and schedule mutation stay
    delegated to the existing generic rotation layers.
    """

    bridge: HealerReserveProtectionBridgeResult
    protection_plan: RotationReserveProtectionPlan
    adjustment: RotationReserveAdjustmentProposal


def propose_healer_reserve_decision(
    *,
    plan: RotationPlan,
    bridge: HealerReserveProtectionBridgeResult,
    priorities: tuple[ReserveProtectionPriority, ...],
) -> HealerReserveDecisionResult:
    """Produce a reserve-preserving healer schedule proposal for one demand.

    Priorities must refer exactly to healer-policy-approved discretionary casts.
    The bridge already excludes protected and neutral healer actions. Bindings
    are derived only from those exact scheduled casts, so the generic adjustment
    layer never needs healer-specific knowledge.
    """

    protection_plan = plan_rotation_reserve_protection(
        analysis=bridge.reserve_analysis,
        priorities=priorities,
    )

    discretionary_by_key = {
        (float(item.action.time_seconds), item.skill_name): item
        for item in bridge.discretionary_actions
    }

    bindings: list[ReserveProtectionActionBinding] = []
    for ranked in protection_plan.selected_to_withhold:
        candidate = ranked.candidate
        key = (float(candidate.time_seconds), candidate.source)
        discretionary = discretionary_by_key.get(key)
        if discretionary is None:
            raise ValueError(
                "healer reserve decision selected a candidate without an exact discretionary action binding: "
                f"{candidate.source} at {candidate.time_seconds:g}s"
            )
        action = discretionary.action
        bindings.append(
            ReserveProtectionActionBinding(
                candidate_time_seconds=candidate.time_seconds,
                candidate_source=candidate.source,
                action_time_seconds=action.time_seconds,
                action_sequence=action.sequence,
            )
        )

    adjustment = propose_rotation_reserve_adjustment(
        plan=plan,
        protection_plan=protection_plan,
        bindings=tuple(bindings),
    )

    return HealerReserveDecisionResult(
        bridge=bridge,
        protection_plan=protection_plan,
        adjustment=adjustment,
    )
