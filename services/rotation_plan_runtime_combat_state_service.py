from __future__ import annotations

import math
from dataclasses import dataclass

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)
from services.rotation_runtime_bar_provenance_service import (
    RotationRuntimeBarProvenanceService,
)


@dataclass(frozen=True)
class RotationPlanRuntimeCombatStateResult:
    """One exact time-resolved combat-state projection for a rotation plan."""

    time_seconds: float
    sequence: int | None
    active_bar: str
    combat_state: CombatState | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.combat_state is not None and not self.unresolved


class RotationPlanRuntimeCombatStateService:
    """Project authoritative runtime history at exact ordered points in a plan.

    Bar identity comes from ``RotationActiveBarAssessor`` so runtime state and
    active-bar legality share one ordered BAR_SWAP authority. Unified runtime effect
    attempts are first bound to that same bar progression by
    ``RotationRuntimeBarProvenanceService``. Skill/gear/potion/group buff truth
    remains owned by ``ExtremeRuntimeSnapshotCombatStateService``; its legacy name is
    retained for compatibility, but the projector is role-neutral.

    The source snapshot must carry unified ``runtime_history``. Legacy one-instant
    ``attempts`` or ``potion_elapsed_seconds`` evidence cannot be stretched across a
    rotation because it does not preserve the event history needed to reconstruct
    another instant honestly.
    """

    def __init__(
        self,
        *,
        active_bar_assessor: RotationActiveBarAssessor | None = None,
        runtime_snapshot_state: ExtremeRuntimeSnapshotCombatStateService | None = None,
        runtime_bar_provenance: RotationRuntimeBarProvenanceService | None = None,
    ) -> None:
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()
        self.runtime_snapshot_state = (
            runtime_snapshot_state or ExtremeRuntimeSnapshotCombatStateService()
        )
        self.runtime_bar_provenance = runtime_bar_provenance or RotationRuntimeBarProvenanceService(
            active_bar_assessor=self.active_bar_assessor
        )

    def resolve(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        plan: RotationPlan,
        runtime_snapshot_source: ExtremeRuntimeSnapshot,
        time_seconds: float,
        sequence: int | None = None,
        initial_bar: str = "front",
        base_combat_state: CombatState = CombatState(),
    ) -> RotationPlanRuntimeCombatStateResult:
        instant = float(time_seconds)
        if not math.isfinite(instant) or instant < 0.0:
            raise ValueError(
                "rotation runtime combat-state time must be finite and non-negative"
            )
        if instant > float(plan.duration_seconds) + 1e-12:
            raise ValueError(
                "rotation runtime combat-state time cannot exceed plan duration"
            )
        boundary_sequence = None if sequence is None else int(sequence)
        if boundary_sequence is not None and boundary_sequence < 0:
            raise ValueError(
                "rotation runtime combat-state sequence cannot be negative"
            )

        active_bar = self.active_bar_assessor.active_bar_at(
            plan,
            time_seconds=instant,
            sequence=boundary_sequence,
            initial_bar=initial_bar,
        )

        if not runtime_snapshot_source.runtime_history:
            return RotationPlanRuntimeCombatStateResult(
                time_seconds=instant,
                sequence=boundary_sequence,
                active_bar=active_bar,
                combat_state=None,
                unresolved=(
                    "time-varying rotation runtime evaluation requires authoritative "
                    "runtime_history; legacy one-snapshot evidence cannot be time-shifted",
                ),
            )

        bound = self.runtime_bar_provenance.bind(
            plan,
            runtime_snapshot_source,
            initial_bar=initial_bar,
        )
        if not bound.resolved or bound.snapshot is None:
            return RotationPlanRuntimeCombatStateResult(
                time_seconds=instant,
                sequence=boundary_sequence,
                active_bar=active_bar,
                combat_state=None,
                unresolved=bound.unresolved,
            )

        snapshot = bound.snapshot.snapshot_at(
            instant,
            sequence=boundary_sequence,
        )
        projected = self.runtime_snapshot_state.resolve(
            build,
            progression=progression,
            active_bar=active_bar,
            snapshot=snapshot,
            base_combat_state=base_combat_state,
        )
        unresolved = tuple(
            dict.fromkeys(
                str(message).strip()
                for message in projected.unresolved
                if str(message).strip()
            )
        )
        return RotationPlanRuntimeCombatStateResult(
            time_seconds=instant,
            sequence=boundary_sequence,
            active_bar=active_bar,
            combat_state=None if unresolved else projected.combat_state,
            unresolved=unresolved,
        )


__all__ = [
    "RotationPlanRuntimeCombatStateResult",
    "RotationPlanRuntimeCombatStateService",
]
