from __future__ import annotations

"""Proof-neutral execute-policy expansion for generated sustained-DPS rotations."""

from dataclasses import dataclass

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_recast import RotationRecastRule
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_execute_filler_opportunity_service import RotationExecuteSnapshotResolver
from services.rotation_execute_filler_policy_service import RotationExecuteFillerPolicyService


@dataclass(frozen=True)
class ExtremeSustainedDPSExecutePolicyCandidate:
    policy_id: str
    candidate: GeneratedRotationCandidate
    mutation_count: int
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class ExtremeSustainedDPSExecutePolicyFrontier:
    candidates: tuple[ExtremeSustainedDPSExecutePolicyCandidate, ...]
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSExecutePolicyFrontierService:
    """Preserve baseline and canonical execute-upgrade policy as distinct variants."""

    def __init__(self, policy_service: RotationExecuteFillerPolicyService) -> None:
        self.policy_service = policy_service

    def expand(
        self,
        *,
        seed: GeneratedRotationCandidate,
        priorities: AbilityPriorityList,
        snapshot_resolver: RotationExecuteSnapshotResolver,
        target_identity: str,
        duration_rules: tuple[RotationRecastRule, ...] = (),
    ) -> ExtremeSustainedDPSExecutePolicyFrontier:
        baseline = ExtremeSustainedDPSExecutePolicyCandidate(
            policy_id="execute:none",
            candidate=seed,
            mutation_count=0,
            evidence=("Baseline plan preserves ordinary filler actions",),
            unresolved=(),
        )
        result = self.policy_service.apply(
            candidate=seed,
            priorities=priorities,
            duration_rules=tuple(duration_rules),
            snapshot_resolver=snapshot_resolver,
            target_identity=target_identity,
        )

        unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in result.unresolved
                if str(item).strip()
            )
        )
        candidates = [baseline]
        if result.mutations:
            candidates.append(
                ExtremeSustainedDPSExecutePolicyCandidate(
                    policy_id="execute:canonical_upgrade",
                    candidate=result.candidate,
                    mutation_count=len(result.mutations),
                    evidence=(
                        f"Canonical execute mutations: {len(result.mutations)}",
                        "Execute opportunity, runtime threshold state, exact-slot damage comparison, and mutation remain canonical shared services",
                    ),
                    unresolved=unresolved,
                )
            )
        elif unresolved:
            candidates.append(
                ExtremeSustainedDPSExecutePolicyCandidate(
                    policy_id="execute:unresolved",
                    candidate=result.candidate,
                    mutation_count=0,
                    evidence=(
                        "Canonical execute policy could not close all required runtime/damage evidence",
                    ),
                    unresolved=unresolved,
                )
            )

        final_unresolved = tuple(
            dict.fromkeys(
                item
                for row in candidates
                for item in row.unresolved
                if item
            )
        )
        return ExtremeSustainedDPSExecutePolicyFrontier(
            candidates=tuple(candidates),
            denominator_proven=not final_unresolved,
            evidence=(
                f"Execute policy variants retained: {len(candidates)}",
                "Baseline remains explicit even when canonical execute mutation is available",
                "No execute is preferred until downstream sustained-DPS simulation scores the whole plan",
            ),
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSExecutePolicyCandidate",
    "ExtremeSustainedDPSExecutePolicyFrontier",
    "ExtremeSustainedDPSExecutePolicyFrontierService",
]
