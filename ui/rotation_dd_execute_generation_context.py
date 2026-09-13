from __future__ import annotations

"""Explicit caller-owned runtime context for DD execute scheduling during Generate."""

from dataclasses import dataclass
from typing import Protocol

from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidenceProvider,
)
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteSnapshotResolver,
)


@dataclass(frozen=True)
class RotationDDExecuteGenerationContext:
    """Facts required to mutate a generated DD plan for execute phase.

    Generate never invents target Health or damage evidence. The caller supplies an
    exact-time target-health snapshot resolver, the target identity represented by
    those snapshots, and the canonical action-damage provider used to compare the
    execute against the currently scheduled filler.
    """

    snapshot_resolver: RotationExecuteSnapshotResolver
    target_identity: str
    action_damage_provider: RotationActionDamageEvidenceProvider

    def __post_init__(self) -> None:
        target = str(self.target_identity or "").strip()
        if not target:
            raise ValueError("DD execute generation context requires target_identity")
        object.__setattr__(self, "target_identity", target)


class RotationDDExecuteGenerationContextResolver(Protocol):
    """Resolve execute runtime facts for one routed generated DD plan."""

    def __call__(
        self,
        *,
        build,
        request,
        generated,
        routed_plan,
    ) -> RotationDDExecuteGenerationContext | None: ...


__all__ = [
    "RotationDDExecuteGenerationContext",
    "RotationDDExecuteGenerationContextResolver",
]
