from __future__ import annotations

from dataclasses import replace

from minmax.rotation_ability_priority import AbilityPriorityList
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
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
    RotationGenerationSupport,
)


_DD_ROLE_KEYS = frozenset({"dd", "dps", "damage", "damage dealer", "damage_dealer"})


class RotationDDCrossBarGenerationSupport:
    """Apply proven DD cross-bar WAIT routing after ordinary generation.

    The base generator remains role-neutral. This wrapper only post-processes saved DD
    plans when callers provide a complete explicit ability-priority list and no
    explicit Ultimate bar is selected. Route discovery, slot feasibility, joint
    selection, and mutation all reuse the canonical services proven by the Phase 13
    audits. Rejected routes remain untouched and therefore continue to fail closed.

    Ultimate-selected generation is deliberately delegated unchanged for now because
    post-generation bar-route mutation could invalidate Ultimate timing/generation
    evidence. That boundary remains explicit instead of fabricating consistency.
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

    def generate(self, *, build, request: RotationGenerationRequest):
        return self.generate_with_evidence(build=build, request=request).plan

    def generate_with_evidence(
        self,
        *,
        build,
        request: RotationGenerationRequest,
    ) -> RotationGenerationResult:
        generated = self.base.generate_with_evidence(build=build, request=request)
        if not self._eligible(build=build, request=request):
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
        if not mutation.applied:
            return generated

        evidence = self.base.duration_evidence.build(mutation.plan)
        return replace(
            generated,
            plan=mutation.plan,
            duration_evidence=evidence,
        )

    @classmethod
    def _eligible(cls, *, build, request: RotationGenerationRequest) -> bool:
        role = str(getattr(build, "Role", "") or "").strip().casefold()
        if role not in _DD_ROLE_KEYS:
            return False
        if not tuple(request.ability_priorities):
            return False
        if str(request.ultimate_bar or "").strip():
            return False
        if bool(request.stabilize_recovery_heavies):
            return False
        return True

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
