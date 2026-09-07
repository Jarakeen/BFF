from __future__ import annotations

from dataclasses import dataclass

from .demand_aware_priority_duration_scheduler import (
    DemandAwarePriorityDurationRotationScheduler,
)
from .rotation_ability_priority import AbilityPriorityList
from .rotation_demand_window import RotationDemandWindow
from .rotation_plan import RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule
from .rotation_wait_decision import PrematureRecastDecisionProvider


@dataclass(frozen=True)
class DemandActionClaim:
    """Explicit permission for one exact skill cast to satisfy one named demand.

    The claim does not alter the skill's verified duration or ordinary refresh rule.
    It may claim one same-bar decision slot inside the named demand only when the
    ordinary next refresh would otherwise occur after the demand window ends.
    """

    demand_name: str
    bar: str
    skill_name: str

    def __post_init__(self) -> None:
        demand = str(self.demand_name or "").strip()
        if not demand:
            raise ValueError("demand action claim requires demand_name")
        object.__setattr__(self, "demand_name", demand)

        bar = str(self.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("demand action claim bar must be front or back")
        object.__setattr__(self, "bar", bar)

        skill = str(self.skill_name or "").strip()
        if not skill:
            raise ValueError("demand action claim requires skill_name")
        object.__setattr__(self, "skill_name", skill)


class DemandActionClaimPriorityDurationRotationScheduler(
    DemandAwarePriorityDurationRotationScheduler
):
    """Demand-aware scheduler with explicit mechanic-driven action claims."""

    def __init__(
        self,
        priorities: AbilityPriorityList,
        demands: tuple[RotationDemandWindow, ...],
        claims: tuple[DemandActionClaim, ...],
    ) -> None:
        super().__init__(priorities, demands)
        self.claims = tuple(claims)
        self._claim_by_key: dict[tuple[str, str, str], DemandActionClaim] = {}
        for claim in self.claims:
            key = (claim.demand_name, claim.bar, claim.skill_name.casefold())
            if key in self._claim_by_key:
                raise ValueError(
                    "duplicate demand action claim for "
                    f"{claim.demand_name}: {claim.skill_name} on {claim.bar} bar"
                )
            self._claim_by_key[key] = claim
        self._consumed_claim_keys: set[tuple[str, str, str]] = set()

    def refine(
        self,
        plan: RotationPlan,
        rules: tuple[RotationRecastRule, ...],
        *,
        wait_decision: PrematureRecastDecisionProvider | None = None,
    ) -> RotationPlan:
        self._validate_claims(tuple(rules))
        self._consumed_claim_keys = set()
        refined = super().refine(plan, rules, wait_decision=wait_decision)
        assumption = (
            "explicit demand action claims may take one same-bar skill slot inside the named demand "
            "only when ordinary refresh would otherwise occur after the demand window"
        )
        if assumption in refined.assumptions:
            return refined
        return RotationPlan(
            character_name=refined.character_name,
            build_name=refined.build_name,
            duration_seconds=refined.duration_seconds,
            actions=refined.actions,
            assumptions=tuple(refined.assumptions) + (assumption,),
            unresolved=refined.unresolved,
        )

    def _validate_claims(self, rules: tuple[RotationRecastRule, ...]) -> None:
        demand_names = {demand.name for demand in self.demands}
        priority_keys = {
            (item.entry.skill_name.casefold(), item.entry.bar)
            for item in self.priorities.resolve()
        }
        rule_keys = {(rule.skill_name.casefold(), rule.bar) for rule in rules}
        for claim in self.claims:
            if claim.demand_name not in demand_names:
                raise ValueError(
                    f"demand action claim references unknown demand {claim.demand_name!r}"
                )
            skill_key = (claim.skill_name.casefold(), claim.bar)
            if skill_key not in priority_keys:
                raise ValueError(
                    "demand action claim targets an ability missing from explicit priorities: "
                    f"{claim.skill_name} on {claim.bar} bar"
                )
            if skill_key not in rule_keys:
                raise ValueError(
                    "demand action claim requires a verified duration rule for "
                    f"{claim.skill_name} on {claim.bar} bar"
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
        ordinary = super()._due_refresh(
            time_seconds=time_seconds,
            bar=bar,
            next_due=next_due,
            rule_order=rule_order,
            action_kind_by_key=action_kind_by_key,
        )
        if ordinary is not None:
            return ordinary

        demand = self._active_demand(time_seconds)
        if demand is None or bar not in {"front", "back"}:
            return None

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

        return None
