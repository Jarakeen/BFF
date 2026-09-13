from __future__ import annotations

"""Compose reviewed execute opportunity discovery and proven filler mutation."""

from dataclasses import dataclass

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_recast import RotationRecastRule
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_execute_filler_mutation_service import (
    RotationExecuteFillerMutation,
    RotationExecuteFillerMutationService,
)
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteFillerOpportunity,
    RotationExecuteFillerOpportunityService,
    RotationExecuteSnapshotResolver,
)


@dataclass(frozen=True)
class RotationExecuteFillerPolicyResult:
    candidate: GeneratedRotationCandidate
    opportunities: tuple[RotationExecuteFillerOpportunity, ...] = ()
    mutations: tuple[RotationExecuteFillerMutation, ...] = ()
    unresolved: tuple[str, ...] = ()


class RotationExecuteFillerPolicyService:
    """Apply execute filler upgrades only through canonical reviewed evidence."""

    def __init__(
        self,
        *,
        opportunity_service: RotationExecuteFillerOpportunityService,
        mutation_service: RotationExecuteFillerMutationService,
    ) -> None:
        self.opportunity_service = opportunity_service
        self.mutation_service = mutation_service

    def apply(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        priorities: AbilityPriorityList,
        duration_rules: tuple[RotationRecastRule, ...] = (),
        snapshot_resolver: RotationExecuteSnapshotResolver,
        target_identity: str,
    ) -> RotationExecuteFillerPolicyResult:
        opportunity = self.opportunity_service.find(
            candidate.plan,
            priorities=priorities,
            duration_rules=duration_rules,
            snapshot_resolver=snapshot_resolver,
            target_identity=target_identity,
        )
        if not opportunity.opportunities:
            return RotationExecuteFillerPolicyResult(
                candidate=candidate,
                opportunities=(),
                mutations=(),
                unresolved=tuple(self._dedupe(list(opportunity.unresolved))),
            )

        mutation = self.mutation_service.apply(
            candidate=candidate,
            opportunities=opportunity.opportunities,
        )
        unresolved = list(opportunity.unresolved)
        unresolved.extend(mutation.unresolved)
        return RotationExecuteFillerPolicyResult(
            candidate=mutation.candidate,
            opportunities=opportunity.opportunities,
            mutations=mutation.mutations,
            unresolved=tuple(self._dedupe(unresolved)),
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


__all__ = [
    "RotationExecuteFillerPolicyResult",
    "RotationExecuteFillerPolicyService",
]
