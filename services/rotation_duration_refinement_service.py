from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.demand_action_claim_anticipatory_duration_scheduler import (
    DemandActionClaimAnticipatoryPriorityDurationRotationScheduler,
)
from minmax.demand_action_claim_duration_scheduler import (
    DemandActionClaim,
    DemandActionClaimPriorityDurationRotationScheduler,
)
from minmax.demand_anticipatory_duration_scheduler import (
    DemandAnticipatoryPriorityDurationRotationScheduler,
    DemandAnticipatoryPrioritySoftActionDurationRotationScheduler,
    DemandRefreshLead,
)
from minmax.demand_aware_priority_duration_scheduler import (
    DemandAwarePriorityDurationRotationScheduler,
    DemandAwarePrioritySoftActionDurationRotationScheduler,
)
from minmax.duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from minmax.priority_aware_duration_scheduler import PriorityAwareDurationRotationScheduler
from minmax.refresh_cadence_duration_scheduler import (
    PriorityAwareRefreshCadenceDurationRotationScheduler,
    PriorityAwareRefreshCadenceSoftActionDurationRotationScheduler,
    RefreshCadenceDurationRotationScheduler,
    RefreshCadenceSoftActionDurationRotationScheduler,
    RotationRefreshIntervalPolicy,
)
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationPlan
from minmax.rotation_wait_decision import PrematureRecastDecisionProvider
from minmax.soft_action_duration_scheduler import (
    PriorityAwareSoftActionDurationRotationScheduler,
    SoftActionDurationRotationScheduler,
)
from services.rotation_duration_analysis_service import (
    RotationDurationAnalysisService,
    RotationDurationProjection,
)


@dataclass(frozen=True)
class RotationDurationRefinement:
    """One duration-aware refinement result with evidence from the final schedule."""

    plan: RotationPlan
    duration_projection: RotationDurationProjection


class RotationDurationRefinementService:
    """Resolve canonical durations, refine a plan, then analyze the final schedule."""

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        duration_analysis: RotationDurationAnalysisService | None = None,
        scheduler: DurationAwareRotationScheduler | None = None,
    ) -> None:
        self.duration_analysis = duration_analysis or RotationDurationAnalysisService(
            database_path
        )
        self.scheduler = scheduler or DurationAwareRotationScheduler()

    def refine(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList | None = None,
        wait_decision: PrematureRecastDecisionProvider | None = None,
        demands: tuple[RotationDemandWindow, ...] = (),
        demand_refresh_leads: tuple[DemandRefreshLead, ...] = (),
        demand_action_claims: tuple[DemandActionClaim, ...] = (),
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...] = (),
    ) -> RotationDurationRefinement:
        # The first projection supplies canonical duration rules used to refine
        # the seed schedule. It is not returned as final evidence because its
        # uptime/gap measurements describe the pre-refinement plan.
        seed_projection = self.duration_analysis.analyze(plan)
        demand_windows = tuple(demands)
        refresh_leads = tuple(demand_refresh_leads)
        action_claims = tuple(demand_action_claims)
        cadence_policies = tuple(refresh_cadences)
        if demand_windows and priorities is None:
            raise ValueError("rotation demand windows require explicit ability priorities")
        if refresh_leads and not demand_windows:
            raise ValueError("demand refresh leads require at least one rotation demand window")
        if refresh_leads and priorities is None:
            raise ValueError("demand refresh leads require explicit ability priorities")
        if action_claims and not demand_windows:
            raise ValueError("demand action claims require at least one rotation demand window")
        if action_claims and priorities is None:
            raise ValueError("demand action claims require explicit ability priorities")
        if action_claims and wait_decision is not None:
            raise ValueError(
                "demand action claims cannot yet be combined with caller-proven soft actions"
            )
        if cadence_policies and (demand_windows or refresh_leads or action_claims):
            raise ValueError(
                "global refresh cadence policy cannot yet be combined with encounter demand scheduling"
            )

        if wait_decision is not None and priorities is not None:
            if cadence_policies:
                scheduler = PriorityAwareRefreshCadenceSoftActionDurationRotationScheduler(
                    priorities,
                    cadence_policies,
                )
            elif refresh_leads:
                scheduler = DemandAnticipatoryPrioritySoftActionDurationRotationScheduler(
                    priorities,
                    demand_windows,
                    refresh_leads,
                )
            elif demand_windows:
                scheduler = DemandAwarePrioritySoftActionDurationRotationScheduler(
                    priorities,
                    demand_windows,
                )
            else:
                scheduler = PriorityAwareSoftActionDurationRotationScheduler(priorities)
            refined = scheduler.refine(
                plan,
                seed_projection.rules,
                wait_decision=wait_decision,
                soft_decision=wait_decision,
            )
        elif wait_decision is not None:
            scheduler = (
                RefreshCadenceSoftActionDurationRotationScheduler(cadence_policies)
                if cadence_policies
                else SoftActionDurationRotationScheduler()
            )
            refined = scheduler.refine(
                plan,
                seed_projection.rules,
                wait_decision=wait_decision,
                soft_decision=wait_decision,
            )
        else:
            if priorities is not None and action_claims and refresh_leads:
                scheduler = DemandActionClaimAnticipatoryPriorityDurationRotationScheduler(
                    priorities,
                    demand_windows,
                    action_claims,
                    refresh_leads,
                )
            elif priorities is not None and action_claims:
                scheduler = DemandActionClaimPriorityDurationRotationScheduler(
                    priorities,
                    demand_windows,
                    action_claims,
                )
            elif priorities is not None and refresh_leads:
                scheduler = DemandAnticipatoryPriorityDurationRotationScheduler(
                    priorities,
                    demand_windows,
                    refresh_leads,
                )
            elif priorities is not None and demand_windows:
                scheduler = DemandAwarePriorityDurationRotationScheduler(
                    priorities,
                    demand_windows,
                )
            elif priorities is not None and cadence_policies:
                scheduler = PriorityAwareRefreshCadenceDurationRotationScheduler(
                    priorities,
                    cadence_policies,
                )
            elif priorities is not None:
                scheduler = PriorityAwareDurationRotationScheduler(priorities)
            elif cadence_policies:
                scheduler = RefreshCadenceDurationRotationScheduler(cadence_policies)
            else:
                scheduler = self.scheduler
            refined = scheduler.refine(
                plan,
                seed_projection.rules,
            )

        unresolved = self._dedupe(
            tuple(refined.unresolved) + tuple(seed_projection.unresolved)
        )
        if unresolved != refined.unresolved:
            refined = self._with_unresolved(refined, unresolved)

        # Re-analyze the actual refined actions so callers receive duration,
        # recast, uptime, and gap evidence for the same plan they render/evaluate.
        final_projection = self.duration_analysis.analyze(refined)
        final_unresolved = self._dedupe(
            tuple(refined.unresolved) + tuple(final_projection.unresolved)
        )
        if final_unresolved != refined.unresolved:
            refined = self._with_unresolved(refined, final_unresolved)

        return RotationDurationRefinement(
            plan=refined,
            duration_projection=final_projection,
        )

    @staticmethod
    def _with_unresolved(
        plan: RotationPlan,
        unresolved: tuple[str, ...],
    ) -> RotationPlan:
        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=plan.actions,
            assumptions=plan.assumptions,
            unresolved=unresolved,
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)
