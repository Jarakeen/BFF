from __future__ import annotations

from dataclasses import replace

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_recast import RotationRecastRule
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_cross_bar_filler_opportunity_service import (
    RotationCrossBarFillerOpportunityService,
)
from services.rotation_cross_bar_route_mutation_service import (
    RotationCrossBarRouteMutationService,
)
from services.rotation_cross_bar_route_proposal_service import (
    RotationCrossBarRouteProposalService,
)
from services.rotation_cross_bar_route_selection_service import (
    RotationCrossBarRouteSelectionService,
)
from services.rotation_cross_bar_route_slot_feasibility_service import (
    RotationCrossBarRouteSlotFeasibilityService,
)
from services.rotation_execute_filler_damage_comparison_service import (
    RotationExecuteFillerDamageComparisonService,
)
from services.rotation_execute_filler_mutation_service import (
    RotationExecuteFillerMutationService,
)
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteFillerOpportunityService,
)
from services.rotation_execute_filler_policy_service import (
    RotationExecuteFillerPolicyService,
)
from ui.rotation_dd_execute_generation_context import (
    RotationDDExecuteGenerationContextResolver,
)
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
    RotationGenerationSupport,
)


_DD_ROLE_KEYS = frozenset({"dd", "dps", "damage", "damage dealer", "damage_dealer"})
_NO_ULTIMATE_BAR_UNRESOLVED = (
    "ultimate timing is not scheduled because no ultimate bar is selected"
)


class RotationDDCrossBarGenerationSupport:
    """Apply proven DD routing and execute policy before selected-Ultimate projection.

    The base generator remains role-neutral. This wrapper only post-processes saved DD
    plans when callers provide a complete explicit ability-priority list. Route
    discovery, slot feasibility, joint selection, and mutation all reuse the canonical
    services proven by the Phase 13 audits. Rejected routes remain untouched and
    therefore continue to fail closed.

    Optional execute scheduling is caller-evidence driven. A supplied execute context
    resolver must provide exact-time target Health snapshots, target identity, and the
    canonical action-damage provider used to compare the reviewed execute against the
    existing filler. Missing execute context leaves the routed plan unchanged.

    When callers explicitly select a slot-6 Ultimate, the wrapper defers only the
    shared Ultimate projection until after DD routing and execute mutation. This keeps
    the canonical Ultimate service as the sole owner of affordability and spend logic
    while preventing later plan mutation from invalidating its timing evidence.
    Recovery-heavy stabilization remains delegated unchanged because its fixed-point
    generation owns a separate iteration boundary.
    """

    def __init__(
        self,
        *,
        base: RotationGenerationSupport | None = None,
        opportunity_service: RotationCrossBarFillerOpportunityService | None = None,
        proposal_service: RotationCrossBarRouteProposalService | None = None,
        feasibility_service: RotationCrossBarRouteSlotFeasibilityService | None = None,
        selection_service: RotationCrossBarRouteSelectionService | None = None,
        mutation_service: RotationCrossBarRouteMutationService | None = None,
        execute_context_resolver: RotationDDExecuteGenerationContextResolver | None = None,
        execute_opportunity_service: RotationExecuteFillerOpportunityService | None = None,
    ) -> None:
        self.base = base or RotationGenerationSupport()
        self.opportunity_service = (
            opportunity_service or RotationCrossBarFillerOpportunityService()
        )
        self.proposal_service = proposal_service or RotationCrossBarRouteProposalService()
        self.feasibility_service = (
            feasibility_service or RotationCrossBarRouteSlotFeasibilityService()
        )
        self.selection_service = selection_service or RotationCrossBarRouteSelectionService()
        self.mutation_service = mutation_service or RotationCrossBarRouteMutationService()
        self.execute_context_resolver = execute_context_resolver
        self.execute_opportunity_service = (
            execute_opportunity_service or RotationExecuteFillerOpportunityService()
        )

    def generate(self, *, build, request: RotationGenerationRequest):
        return self.generate_with_evidence(build=build, request=request).plan

    def generate_with_evidence(
        self,
        *,
        build,
        request: RotationGenerationRequest,
    ) -> RotationGenerationResult:
        eligible = self._eligible(build=build, request=request)
        selected_ultimate_bar = str(request.ultimate_bar or "").strip().casefold()
        if eligible and selected_ultimate_bar not in {"", "front", "back"}:
            raise ValueError("ultimate bar must be 'front', 'back', or blank")

        defer_ultimate = eligible and bool(selected_ultimate_bar)
        base_request = replace(request, ultimate_bar="") if defer_ultimate else request
        generated = self.base.generate_with_evidence(build=build, request=base_request)
        if not eligible:
            return generated

        priority_list = AbilityPriorityList(
            character_name=self._character_name(build),
            build_name=str(getattr(build, "BuildName", "") or "").strip(),
            role=str(getattr(build, "Role", "") or "Unspecified").strip(),
            entries=tuple(request.ability_priorities),
        )
        opportunities = self.opportunity_service.find(
            generated.plan,
            priorities=priority_list,
        )
        proposals = self.proposal_service.propose(generated.plan, opportunities)
        feasibility = self.feasibility_service.assess(generated.plan, proposals)
        selection = self.selection_service.select(
            generated.plan,
            proposals,
            feasibility,
        )
        mutation = self.mutation_service.apply(
            generated.plan,
            selection,
            weave_light_attacks=bool(request.weave_light_attacks),
            initial_bar=self._initial_bar(build),
        )
        routed_plan = mutation.plan if mutation.applied else generated.plan
        execute_plan, execute_applied = self._apply_execute_policy(
            build=build,
            request=request,
            generated=generated,
            routed_plan=routed_plan,
            priorities=priority_list,
        )

        if defer_ultimate:
            pre_ultimate_plan = self._prepare_deferred_ultimate_plan(
                execute_plan,
                selected_ultimate_bar=selected_ultimate_bar,
                use_scheduled_combat_attacks=bool(
                    request.use_scheduled_combat_attacks_for_ultimate
                ),
            )
            projection = self.base.ultimate_service.apply_generation(
                build=build,
                plan=pre_ultimate_plan,
                ultimate_bar=selected_ultimate_bar,
                starting_ultimate=float(request.starting_ultimate),
                use_scheduled_combat_attacks=bool(
                    request.use_scheduled_combat_attacks_for_ultimate
                ),
            )
            final_plan = projection.plan
            evidence = self.base.duration_evidence.build(final_plan)
            return replace(
                generated,
                plan=final_plan,
                duration_evidence=evidence,
                ultimate_projection=projection,
            )

        if not mutation.applied and not execute_applied:
            return generated

        evidence = self.base.duration_evidence.build(execute_plan)
        return replace(
            generated,
            plan=execute_plan,
            duration_evidence=evidence,
        )

    def _apply_execute_policy(
        self,
        *,
        build,
        request: RotationGenerationRequest,
        generated: RotationGenerationResult,
        routed_plan,
        priorities: AbilityPriorityList,
    ):
        if self.execute_context_resolver is None:
            return routed_plan, False
        context = self.execute_context_resolver(
            build=build,
            request=request,
            generated=generated,
            routed_plan=routed_plan,
        )
        if context is None:
            return routed_plan, False

        duration_rules = tuple(
            RotationRecastRule(
                skill_name=row.ability,
                duration_seconds=float(row.duration_seconds),
                bar=(
                    str(row.bar).strip().casefold()
                    if str(row.bar).strip().casefold() in {"front", "back"}
                    else None
                ),
            )
            for row in generated.duration_evidence.rows
            if float(row.duration_seconds) > 0.0
        )
        comparison = RotationExecuteFillerDamageComparisonService(
            action_damage_provider=context.action_damage_provider,
        )
        execute_mutation = RotationExecuteFillerMutationService(
            comparison_service=comparison,
        )
        policy = RotationExecuteFillerPolicyService(
            opportunity_service=self.execute_opportunity_service,
            mutation_service=execute_mutation,
        )
        candidate = GeneratedRotationCandidate(
            candidate_id="dashboard_execute",
            plan=routed_plan,
            refresh_leads=(),
            action_claims=(),
        )
        result = policy.apply(
            candidate=candidate,
            priorities=priorities,
            duration_rules=duration_rules,
            snapshot_resolver=context.snapshot_resolver,
            target_identity=context.target_identity,
        )
        if not result.mutations:
            return routed_plan, False
        return result.candidate.plan, True

    @classmethod
    def _eligible(cls, *, build, request: RotationGenerationRequest) -> bool:
        role = str(getattr(build, "Role", "") or "").strip().casefold()
        if role not in _DD_ROLE_KEYS:
            return False
        if not tuple(request.ability_priorities):
            return False
        if bool(request.stabilize_recovery_heavies):
            return False
        return True

    @classmethod
    def _prepare_deferred_ultimate_plan(
        cls,
        plan,
        *,
        selected_ultimate_bar: str,
        use_scheduled_combat_attacks: bool,
    ):
        assumptions = list(plan.assumptions)
        assumptions.append(
            f"dashboard Ultimate projection explicitly selects the {selected_ultimate_bar} slot-6 ultimate"
        )
        if use_scheduled_combat_attacks:
            assumptions.append(
                "scheduled light/heavy attacks are treated as successful damaging attacks for base Ultimate generation"
            )
        unresolved = tuple(
            value
            for value in plan.unresolved
            if str(value or "").strip().casefold()
            != _NO_ULTIMATE_BAR_UNRESOLVED.casefold()
        )
        return replace(
            plan,
            assumptions=tuple(cls._dedupe(assumptions)),
            unresolved=unresolved,
        )

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    @staticmethod
    def _initial_bar(build) -> str:
        front = [
            str(value or "").strip()
            for value in list(getattr(build, "FrontBarSkills", []) or [])[:5]
            if str(value or "").strip()
        ]
        return "front" if front else "back"

    @staticmethod
    def _character_name(build) -> str:
        return str(
            getattr(build, "CharacterName", "")
            or getattr(build, "Name", "")
            or getattr(build, "Gamertag", "")
            or ""
        ).strip()


__all__ = ["RotationDDCrossBarGenerationSupport"]
