from __future__ import annotations

"""Evidence-gated runtime-policy axes for generated sustained-DPS rotations.

The adapter begins with one selected delayed-Ultimate plan, wraps that exact plan as a
GeneratedRotationCandidate, then exposes canonical execute and Heavy Attack policy
frontiers. Legacy mode consumes caller-reviewed Heavy Attack windows and keeps explicit
omitted scope. Complete-discovery mode derives every scheduler-legal 1.8s Heavy Attack
start from each finalized execute plan and requires a proven encounter channel-block
denominator before exposing omission-free heavy_attack_policy coverage.
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
from services.extreme_sustained_dps_heavy_attack_window_discovery_service import (
    ExtremeSustainedDPSHeavyAttackChannelBlock,
    ExtremeSustainedDPSHeavyAttackWindowDiscoveryService,
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
    heavy_attack_channel_blocks: tuple[ExtremeSustainedDPSHeavyAttackChannelBlock, ...] = ()
    heavy_attack_channel_block_denominator_proven: bool = False
    execute_policy: ExtremeSustainedDPSExecutePolicyCandidate | None = None
    heavy_attack_policy: ExtremeSustainedDPSHeavyAttackPolicyCandidate | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.seed, GeneratedRotationCandidate):
            raise TypeError("generated runtime-policy state requires a GeneratedRotationCandidate seed")
        if not isinstance(self.target_identity, str) or not self.target_identity.strip():
            raise ValueError("generated runtime-policy state requires target_identity")
        for label, value in (
            ("duration_rules", self.duration_rules),
            ("heavy_attack_windows", self.heavy_attack_windows),
            ("heavy_attack_channel_blocks", self.heavy_attack_channel_blocks),
        ):
            if not isinstance(value, tuple):
                raise TypeError(f"generated runtime-policy state {label} must be a tuple")
        if not isinstance(self.heavy_attack_channel_block_denominator_proven, bool):
            raise TypeError(
                "generated runtime-policy state Heavy Attack channel-block denominator proof must be boolean"
            )

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
    """Adapt execute plus legacy or complete-discovery Heavy Attack families into tree axes."""

    def __init__(
        self,
        *,
        execute_policies: ExtremeSustainedDPSExecutePolicyFrontierService | object,
        heavy_attack_policies: (
            ExtremeSustainedDPSHeavyAttackPolicyFrontierService | object
        ),
        heavy_attack_window_discovery: object | None = None,
        require_complete_heavy_attack_discovery: bool = False,
    ) -> None:
        self.execute_policies = execute_policies
        self.heavy_attack_policies = heavy_attack_policies
        self.heavy_attack_window_discovery = (
            heavy_attack_window_discovery
            or ExtremeSustainedDPSHeavyAttackWindowDiscoveryService
        )
        if not isinstance(require_complete_heavy_attack_discovery, bool):
            raise TypeError("complete Heavy Attack discovery flag must be boolean")
        self.require_complete_heavy_attack_discovery = require_complete_heavy_attack_discovery

    @staticmethod
    def _proven_candidates(frontier: object, label: str) -> tuple[object, ...]:
        candidates = getattr(frontier, "candidates", ())
        if not isinstance(candidates, tuple):
            raise TypeError(f"{label} candidates must be a tuple")
        unresolved = getattr(frontier, "unresolved", ())
        if not isinstance(unresolved, tuple):
            raise TypeError(f"{label} unresolved evidence must be a tuple")
        denominator_proven = getattr(frontier, "denominator_proven", False)
        if not isinstance(denominator_proven, bool):
            raise TypeError(f"{label} denominator proof flag must be boolean")
        if not denominator_proven:
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
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("execute policy candidate index must be an integer")
        target = index
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

        if self.require_complete_heavy_attack_discovery:
            if not state.heavy_attack_channel_block_denominator_proven:
                raise ValueError(
                    "complete Heavy Attack discovery mode requires a proven encounter channel-block denominator"
                )
            discovery = self.heavy_attack_window_discovery.discover(
                seed=execute.candidate,
                duration_rules=state.duration_rules,
                priorities=state.priorities,
                channel_blocks=state.heavy_attack_channel_blocks,
                channel_block_denominator_proven=True,
            )
            discovery_proven = getattr(discovery, "denominator_proven", None)
            if not isinstance(discovery_proven, bool):
                raise TypeError(
                    "Heavy Attack window discovery denominator proof flag must be boolean"
                )
            discovery_unresolved = getattr(discovery, "unresolved", ())
            if not isinstance(discovery_unresolved, tuple):
                raise TypeError(
                    "Heavy Attack window discovery unresolved evidence must be a tuple"
                )
            if not discovery_proven:
                detail = "; ".join(discovery_unresolved)
                raise ValueError(
                    "Heavy Attack window discovery denominator is unresolved"
                    + (f": {detail}" if detail else "")
                )

            def materialize(selected):
                return self.heavy_attack_window_discovery.materialize(
                    seed=execute.candidate,
                    windows=tuple(selected),
                    duration_rules=state.duration_rules,
                    priorities=state.priorities,
                    channel_blocks=state.heavy_attack_channel_blocks,
                )

            return self.heavy_attack_policies.expand(
                seed=execute.candidate,
                windows=discovery.windows,
                candidate_materializer=materialize,
            )

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
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("Heavy Attack policy candidate index must be an integer")
        target = index
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
        heavy_attack_channel_blocks: tuple[
            ExtremeSustainedDPSHeavyAttackChannelBlock,
            ...,
        ] = (),
        heavy_attack_channel_block_denominator_proven: bool = False,
    ) -> ExtremeSustainedDPSGeneratedRuntimePolicyAxisState:
        identity = str(candidate_id or "").strip()
        if not identity:
            raise ValueError("generated runtime-policy candidate_id is required")
        target = str(target_identity or "").strip()
        if not target:
            raise ValueError("generated execute target identity is required")
        if snapshot_resolver is None:
            raise ValueError("generated execute snapshot resolver is required")
        for label, value in (
            ("duration_rules", duration_rules),
            ("heavy_attack_windows", heavy_attack_windows),
            ("heavy_attack_channel_blocks", heavy_attack_channel_blocks),
        ):
            if not isinstance(value, tuple):
                raise TypeError(f"generated runtime-policy {label} must be a tuple")
        if not isinstance(heavy_attack_channel_block_denominator_proven, bool):
            raise TypeError(
                "generated runtime-policy Heavy Attack channel-block denominator proof must be boolean"
            )

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
            duration_rules=duration_rules,
            heavy_attack_windows=heavy_attack_windows,
            heavy_attack_channel_blocks=heavy_attack_channel_blocks,
            heavy_attack_channel_block_denominator_proven=(
                heavy_attack_channel_block_denominator_proven
            ),
        )

    def axes(self) -> tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...]:
        return (
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Execute Policy",
                candidate_count=self._execute_count,
                candidate_at=self._execute_at,
                canonical_axes=("execute_policy",),
            ),
            ExtremeSustainedDPSIndexedFrontierAxis(
                (
                    "Heavy Attack Policy"
                    if self.require_complete_heavy_attack_discovery
                    else "Reviewed Heavy Attack Policy"
                ),
                candidate_count=self._heavy_count,
                candidate_at=self._heavy_at,
                canonical_axes=("heavy_attack_policy",),
                omitted_scope=(
                    ()
                    if self.require_complete_heavy_attack_discovery
                    else (
                        "Heavy Attack windows outside the caller-supplied reviewed safe set are not claimed closed",
                    )
                ),
            ),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedRuntimePolicyAxisAdapterService",
    "ExtremeSustainedDPSGeneratedRuntimePolicyAxisState",
]
