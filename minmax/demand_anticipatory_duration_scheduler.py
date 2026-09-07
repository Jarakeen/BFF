from __future__ import annotations

from dataclasses import dataclass
import math

from .demand_aware_priority_duration_scheduler import (
    DemandAwarePriorityDurationRotationScheduler,
    DemandAwarePrioritySoftActionDurationRotationScheduler,
)
from .rotation_ability_priority import AbilityPriorityList
from .rotation_demand_window import RotationDemandWindow
from .rotation_plan import RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule
from .rotation_wait_decision import PrematureRecastDecisionProvider


@dataclass(frozen=True)
class DemandRefreshLead:
    """Explicit permission to refresh one ability early during one named demand.

    ``lead_seconds`` is additional early-refresh permission relative to the normal
    verified refresh due time. It does not change the ability's canonical duration
    or its ordinary refresh policy outside the named demand window.
    """

    demand_name: str
    bar: str
    skill_name: str
    lead_seconds: float

    def __post_init__(self) -> None:
        demand = str(self.demand_name or "").strip()
        if not demand:
            raise ValueError("demand refresh lead requires demand_name")
        object.__setattr__(self, "demand_name", demand)

        bar = str(self.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("demand refresh lead bar must be front or back")
        object.__setattr__(self, "bar", bar)

        skill = str(self.skill_name or "").strip()
        if not skill:
            raise ValueError("demand refresh lead requires skill_name")
        object.__setattr__(self, "skill_name", skill)

        lead = float(self.lead_seconds)
        if not math.isfinite(lead) or lead <= 0:
            raise ValueError("demand refresh lead must be finite and positive")
        object.__setattr__(self, "lead_seconds", lead)


class _DemandAnticipationMixin:
    def _configure_demand_refresh_leads(
        self,
        refresh_leads: tuple[DemandRefreshLead, ...],
    ) -> None:
        by_key: dict[tuple[str, str, str], DemandRefreshLead] = {}
        for item in refresh_leads:
            key = (item.demand_name, item.skill_name.casefold(), item.bar)
            if key in by_key:
                raise ValueError(
                    "duplicate demand refresh lead for "
                    f"{item.demand_name}: {item.skill_name} on {item.bar} bar"
                )
            by_key[key] = item
        self.demand_refresh_leads = tuple(refresh_leads)
        self._demand_refresh_lead_by_key = by_key

    def _validate_demand_refresh_leads(
        self,
        rules: tuple[RotationRecastRule, ...],
    ) -> None:
        rule_by_key = {
            (rule.skill_name.casefold(), rule.bar): rule
            for rule in rules
        }
        demand_names = {demand.name for demand in self.demands}
        priority_keys = {
            (item.entry.skill_name.casefold(), item.entry.bar)
            for item in self.priorities.resolve()
        }
        for item in self.demand_refresh_leads:
            if item.demand_name not in demand_names:
                raise ValueError(
                    f"demand refresh lead references unknown demand {item.demand_name!r}"
                )
            key = (item.skill_name.casefold(), item.bar)
            if key not in priority_keys:
                raise ValueError(
                    "demand refresh lead targets an ability missing from explicit priorities: "
                    f"{item.skill_name} on {item.bar} bar"
                )
            rule = rule_by_key.get(key)
            if rule is None:
                raise ValueError(
                    "demand refresh lead requires a verified duration rule for "
                    f"{item.skill_name} on {item.bar} bar"
                )
            ordinary_refresh_span = rule.duration_seconds - rule.refresh_lead_seconds
            if item.lead_seconds >= ordinary_refresh_span:
                raise ValueError(
                    "demand refresh lead must remain shorter than the verified ordinary "
                    f"refresh span for {item.skill_name}"
                )

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
        priority_by_key = {
            (item.entry.skill_name.casefold(), item.entry.bar): (
                item.effective_priority,
                item.entry.slot,
            )
            for item in self.priorities.resolve(demand)
        }

        candidates = []
        for key, due in next_due.items():
            if key[1] != bar or action_kind_by_key.get(key) is not RotationActionKind.SKILL:
                continue

            effective_due = float(due)
            if demand is not None:
                lead = self._demand_refresh_lead_by_key.get(
                    (demand.name, key[0], key[1] or "")
                )
                if lead is not None:
                    effective_due -= lead.lead_seconds

            if effective_due > time_seconds:
                continue

            priority, slot = priority_by_key.get(
                key,
                (10**9, rule_order.get(key, 10**9)),
            )
            candidates.append(
                (
                    priority,
                    effective_due,
                    due,
                    slot,
                    rule_order.get(key, 10**9),
                    key,
                )
            )

        if not candidates:
            return None
        candidates.sort(
            key=lambda item: (item[0], item[1], item[2], item[3], item[4], item[5][0])
        )
        return candidates[0][5]


class DemandAnticipatoryPriorityDurationRotationScheduler(
    _DemandAnticipationMixin,
    DemandAwarePriorityDurationRotationScheduler,
):
    """Demand-aware priority scheduler with explicit early-refresh permission."""

    def __init__(
        self,
        priorities: AbilityPriorityList,
        demands: tuple[RotationDemandWindow, ...],
        refresh_leads: tuple[DemandRefreshLead, ...],
    ) -> None:
        DemandAwarePriorityDurationRotationScheduler.__init__(self, priorities, demands)
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


class DemandAnticipatoryPrioritySoftActionDurationRotationScheduler(
    _DemandAnticipationMixin,
    DemandAwarePrioritySoftActionDurationRotationScheduler,
):
    """Demand anticipation plus the existing caller-proven soft action seam."""

    def __init__(
        self,
        priorities: AbilityPriorityList,
        demands: tuple[RotationDemandWindow, ...],
        refresh_leads: tuple[DemandRefreshLead, ...],
    ) -> None:
        DemandAwarePrioritySoftActionDurationRotationScheduler.__init__(
            self,
            priorities,
            demands,
        )
        self._configure_demand_refresh_leads(tuple(refresh_leads))

    def refine(self, plan, rules, *, wait_decision=None, soft_decision=None):
        self._validate_demand_refresh_leads(tuple(rules))
        return super().refine(
            plan,
            rules,
            wait_decision=wait_decision,
            soft_decision=soft_decision,
        )
