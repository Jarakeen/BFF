from __future__ import annotations

from .demand_action_claim_duration_scheduler import (
    DemandActionClaim,
    DemandActionClaimPriorityDurationRotationScheduler,
)
from .demand_anticipatory_duration_scheduler import (
    DemandRefreshLead,
    _DemandAnticipationMixin,
)
from .rotation_ability_priority import AbilityPriorityList
from .rotation_demand_window import RotationDemandWindow
from .rotation_plan import RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule
from .rotation_wait_decision import PrematureRecastDecisionProvider


class DemandActionClaimAnticipatoryPriorityDurationRotationScheduler(
    _DemandAnticipationMixin,
    DemandActionClaimPriorityDurationRotationScheduler,
):
    """Demand-aware scheduler supporting both hard claims and early refresh leads.

    Explicit mechanic action claims have first right to a same-bar decision slot
    when the claimed skill would otherwise miss the active demand window. If no
    claim is eligible, the ordinary anticipatory refresh policy decides among due
    and caller-permitted early refreshes using the active demand priorities.

    The two policy types remain permissions, not duration mutations. Verified
    duration rules continue to define ordinary recast timing for every skill.
    """

    def __init__(
        self,
        priorities: AbilityPriorityList,
        demands: tuple[RotationDemandWindow, ...],
        claims: tuple[DemandActionClaim, ...],
        refresh_leads: tuple[DemandRefreshLead, ...],
    ) -> None:
        DemandActionClaimPriorityDurationRotationScheduler.__init__(
            self,
            priorities,
            demands,
            claims,
        )
        self._configure_demand_refresh_leads(tuple(refresh_leads))

    def refine(
        self,
        plan: RotationPlan,
        rules: tuple[RotationRecastRule, ...],
        *,
        wait_decision: PrematureRecastDecisionProvider | None = None,
    ) -> RotationPlan:
        self._validate_demand_refresh_leads(tuple(rules))
        return super().refine(plan, rules, wait_decision=wait_decision)

    def _due_refresh(
        self,
        *,
        time_seconds: float,
        bar: str | None,
        next_due: dict[tuple[str, str | None], float],
        rule_order: dict[tuple[str, str | None], int],
        action_kind_by_key: dict[tuple[str, str | None], RotationActionKind],
    ) -> tuple[str, str | None] | None:
        demand = self._active_demand(time_seconds)
        if demand is not None and bar in {"front", "back"}:
            for claim in self.claims:
                if claim.demand_name != demand.name or claim.bar != bar:
                    continue
                claim_key = (claim.demand_name, claim.bar, claim.skill_name.casefold())
                if claim_key in self._consumed_claim_keys:
                    continue

                skill_key = (claim.skill_name.casefold(), claim.bar)
                due = next_due.get(skill_key)
                if due is None:
                    continue
                if float(due) <= float(demand.end_seconds):
                    continue

                self._consumed_claim_keys.add(claim_key)
                return skill_key

        return _DemandAnticipationMixin._due_refresh(
            self,
            time_seconds=time_seconds,
            bar=bar,
            next_due=next_due,
            rule_order=rule_order,
            action_kind_by_key=action_kind_by_key,
        )


__all__ = ["DemandActionClaimAnticipatoryPriorityDurationRotationScheduler"]
