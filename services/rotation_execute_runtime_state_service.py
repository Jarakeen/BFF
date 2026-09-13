from __future__ import annotations

"""Resolve reviewed execute evidence against explicit runtime target Health.

This layer is scheduler-neutral.  It does not decide which execute should be cast,
replace fillers, or alter cadence.  It only answers whether canonical threshold
execute evidence is active, inactive, or unresolved for one CombatStateSnapshot.

Missing candidate evidence, missing target identity, or unknown target Health all
fail closed as UNKNOWN rather than being treated as inactive execute behavior.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.combat_state_snapshot import CombatStateSnapshot
from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidence,
    RotationExecuteComponentEvidence,
)


class RotationExecuteRuntimeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RotationExecuteRuntimeState:
    status: RotationExecuteRuntimeStatus
    target_identity: str
    active_components: tuple[RotationExecuteComponentEvidence, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def active(self) -> bool:
        return self.status is RotationExecuteRuntimeStatus.ACTIVE


class RotationExecuteRuntimeStateService:
    """Evaluate threshold execute evidence against one explicit runtime snapshot."""

    def resolve(
        self,
        *,
        candidate: RotationExecuteCandidateEvidence,
        snapshot: CombatStateSnapshot,
        target_identity: str,
    ) -> RotationExecuteRuntimeState:
        target = str(target_identity or "").strip()
        if not target:
            return RotationExecuteRuntimeState(
                status=RotationExecuteRuntimeStatus.UNKNOWN,
                target_identity="",
                unresolved=("execute runtime target identity is required",),
            )

        if not candidate.components:
            reason = (
                tuple(candidate.unresolved)
                or (
                    f"no canonical target-health threshold execute evidence for "
                    f"{candidate.requested_skill_name!r}",
                )
            )
            return RotationExecuteRuntimeState(
                status=RotationExecuteRuntimeStatus.UNKNOWN,
                target_identity=target,
                unresolved=reason,
            )

        target_snapshot = snapshot.target(target)
        if target_snapshot is None:
            return RotationExecuteRuntimeState(
                status=RotationExecuteRuntimeStatus.UNKNOWN,
                target_identity=target,
                unresolved=(f"execute runtime target {target!r} is absent from snapshot",),
            )
        if target_snapshot.health_fraction() is None:
            return RotationExecuteRuntimeState(
                status=RotationExecuteRuntimeStatus.UNKNOWN,
                target_identity=target,
                unresolved=(f"execute runtime target {target!r} Health is unknown",),
            )

        active: list[RotationExecuteComponentEvidence] = []
        unknown = False
        for component in candidate.components:
            state = snapshot.meets_health_threshold(
                float(component.threshold),
                target=target,
            )
            if state is True:
                active.append(component)
            elif state is None:
                unknown = True

        if active:
            return RotationExecuteRuntimeState(
                status=RotationExecuteRuntimeStatus.ACTIVE,
                target_identity=target,
                active_components=tuple(active),
            )
        if unknown:
            return RotationExecuteRuntimeState(
                status=RotationExecuteRuntimeStatus.UNKNOWN,
                target_identity=target,
                unresolved=(f"execute runtime target {target!r} threshold state is unknown",),
            )
        return RotationExecuteRuntimeState(
            status=RotationExecuteRuntimeStatus.INACTIVE,
            target_identity=target,
        )


__all__ = [
    "RotationExecuteRuntimeState",
    "RotationExecuteRuntimeStateService",
    "RotationExecuteRuntimeStatus",
]
