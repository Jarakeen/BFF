from __future__ import annotations

"""Evidence-gated runtime-policy axes for generated sustained-DPS rotations.

This adapter begins with one selected anchored Ultimate/potion plan, wraps that exact
plan as a GeneratedRotationCandidate, then exposes canonical execute and Heavy Attack
policy frontiers as ordered indexed axes. The caller remains responsible for explicit
execute snapshots/target identity and reviewed Heavy Attack windows; traversal over
those supplied families does not claim a broader runtime-policy denominator.
"""

from dataclasses import dataclass, replace

from services.extreme_sustained_dps_execute_policy_frontier_service import (
    ExtremeSustainedDPSExecutePolicyCandidate,
    ExtremeSustainedDPSExecutePolicyFrontierService,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_heavy_attack_policy_frontier_service import (
    ExtremeSustainedDPSHeavyAttackPolicyCandidate,
    ExtremeSustainedDPSHeavyAttackPolicyFrontierService,
    ExtremeSustainedDPSHeavyAttackWindow,
)
from services.extreme_sustained_dps_rotation_policy_frontier_service import (
    ExtremeSustainedDPSRotationPolicyCandidate,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedRuntimePolicyAxisState:
    seed: GeneratedRotationCandidate
    priorities: object
    snapshot_resolver: object
    target_identity: str
    duration_rules: tuple[object, ...] = ()
    heavy_attack_windows: tuple[ExtremeSustainedDPSHeavyAttackWindow, ...] = ()
    execute_policy: ExtremeSustainedDPSExecutePolicyCandidate | None = None
    heavy_attack_policy: ExtremeSustainedDPSHeavyAttackPolicyCandidate | None = None

    @property
    def current_candidate(self) -> GeneratedRotationCandidate:
        if self.heavy_attack_policy is not None:
            return self.heavy_attack_policy.candidate
        if self.execute_policy is not None:
            return self.execute_policy.candidate
        return self.seed

    @property
    def complete(self) -> bool:
        return self.heavy_attack_policy is not None


class ExtremeSustainedDPSGeneratedRuntimePolicyAxisAdapterService:
    """Adapt explicit execute and reviewed Heavy Attack families into tree axes."""

    def __init__(
        self,
        *,
        execute_policies: ExtremeSustainedDPSExecutePolicyFrontierService | object,
        heavy_attack_policies: (
            ExtremeSustainedDPSHeavyAttackPolicyFrontierService | object
        ),
    ) -> None:
        self.execute_policies = execute_policies
        self.heavy_attack_policies = heavy_attack_policies

    @staticmethod
    def _proven_candidates(frontier: object, label: str) -> tuple[object, ...]:
        candidates = tuple(getattr(frontier, "candidates", ()) or ())
        unresolved = tuple(getattr(frontier, "unresolved", ()) or ())
        if not bool(getattr(frontier, "denominator_proven", False)):
            detail = "; ".join(str(item) for item in unresolved if str(item))
            raise ValueError(
                f"{label} denominator is unresolved"
                + (f": {detail}" if detail else "")
            )
        if not candidates:
            raise ValueError(f"{label} denominator is empty")
        return candidates

    def _execute_frontier(
        self,
        state: ExtremeSustainedDPSGeneratedRuntimePolicyAxisState,
    ) -> object:
        return self.execute_policies.expand(
            seed=state.seed,
            priorities=state.priorities,
            snapshot_resolver=state.snapshot_resolver,
            target_identity=state.target_identity,
            duration_rules=state.duration_rules,
        )

    def _execute_count(
        self,
        state: ExtremeSustainedDPSGeneratedRuntimePolicyAxisState,
    ) -> int:
        return len(
            self._proven_candidates(
                self._execute_frontier(state),
                "execute policy frontier",
            )
        )

    def _execute_at(
        self,
        state: ExtremeSustainedDPSGeneratedRuntimePolicyAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedRuntimePolicyAxisState:
        candidates = self._proven_candidates(
            self._execute_frontier(state),
            "execute policy frontier",
        )
        target = int(index)
        if target < 0 or target >= len(candidates):
            raise IndexError("execute policy candidate index out of range")
        return replace(
            state,
            execute_policy=candidates[target],
            heavy_attack_policy=None,
        )

    @staticmethod
    def _require_execute(
        state: ExtremeSustainedDPSGeneratedRuntimePolicyAxisState,
    ) -> ExtremeSustainedDPSExecutePolicyCandidate:
        if state.execute_policy is None:
            raise ValueError(
                "generated Heavy Attack policy requires a selected execute policy"
            )
        return state.execute_policy

    def _heavy_frontier(
        self,
        state: ExtremeSustainedDPSGeneratedRuntimePolicyAxisState,
    ) -> object:
        execute = self._require_execute(state)
        return self.heavy_attack_policies.expand(
            seed=execute.candidate,
            windows=state.heavy_attack_windows,
        )

    def _heavy_count(
        self,
        state: ExtremeSustainedDPSGeneratedRuntimePolicyAxisState,
    ) -> int:
        return len(
            self._proven_candidates(
                self._heavy_frontier(state),
                "Heavy Attack policy frontier",
            )
        )

    def _heavy_at(
        self,
        state: ExtremeSustainedDPSGeneratedRuntimePolicyAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedRuntimePolicyAxisState:
        candidates = self._proven_candidates(
            self._heavy_frontier(state),
            "Heavy Attack policy frontier",
        )
        target = int(index)
        if target < 0 or target >= len(candidates):
            raise IndexError("Heavy Attack policy candidate index out of range")
        return replace(state, heavy_attack_policy=candidates[target])

    def root(
        self,
        rotation_policy: ExtremeSustainedDPSRotationPolicyCandidate,
        *,
        candidate_id: str,
        priorities: object,
        snapshot_resolver: object,
        target_identity: str,
        duration_rules: tuple[object, ...] = (),
        heavy_attack_windows: tuple[
            ExtremeSustainedDPSHeavyAttackWindow,
            ...,
        ] = (),
    ) -> ExtremeSustainedDPSGeneratedRuntimePolicyAxisState:
        identity = str(candidate_id or "").strip()
        if not identity:
            raise ValueError("generated runtime-policy candidate_id is required")
        target = str(target_identity or "").strip()
        if not target:
            raise ValueError("generated execute target identity is required")
        if snapshot_resolver is None:
            raise ValueError("generated execute snapshot resolver is required")

        seed = GeneratedRotationCandidate(
            candidate_id=identity,
            plan=rotation_policy.plan,
            refresh_leads=(),
            action_claims=(),
        )
        return ExtremeSustainedDPSGeneratedRuntimePolicyAxisState(
            seed=seed,
            priorities=priorities,
            snapshot_resolver=snapshot_resolver,
            target_identity=target,
            duration_rules=tuple(duration_rules),
            heavy_attack_windows=tuple(heavy_attack_windows),
        )

    def axes(self) -> tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...]:
        return (
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Execute Policy",
                candidate_count=self._execute_count,
                candidate_at=self._execute_at,
            ),
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Reviewed Heavy Attack Policy",
                candidate_count=self._heavy_count,
                candidate_at=self._heavy_at,
            ),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedRuntimePolicyAxisAdapterService",
    "ExtremeSustainedDPSGeneratedRuntimePolicyAxisState",
]
