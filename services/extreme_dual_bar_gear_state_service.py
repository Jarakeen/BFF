from __future__ import annotations

"""Compose a full two-bar Extreme gear state from proven named realizations.

The existing named realization service proves one active-snapshot equipment
witness.  This layer keeps body/jewelry shared and allows front/back weapon
assignments to differ without duplicating gear math.  Canonical set activation is
still owned by ``GearStatInputResolver``; this service only constructs and audits
legal two-bar materialization.

A front/back pair is composable only when its shared body/jewelry assignments are
identical.  Weapon assignments are bar-local.  This deliberately fails closed
rather than trying to reconcile two snapshots that disagree about shared gear.
"""

from dataclasses import dataclass

from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import PlayerBuild
from services.extreme_named_gear_build_materializer_service import (
    ExtremeNamedGearBuildMaterializerService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)


@dataclass(frozen=True)
class ExtremeDualBarGearState:
    front: ExtremeNamedGearSetRealization
    back: ExtremeNamedGearSetRealization

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.front.topology_signature,
            self.front.set_ids,
            self.front.counts,
            self.front.weapon_shape.value,
            self.back.topology_signature,
            self.back.set_ids,
            self.back.counts,
            self.back.weapon_shape.value,
        )


class ExtremeDualBarGearStateService:
    """Validate and materialize a paired front/back named-gear state."""

    @staticmethod
    def _shared_assignment_key(
        realization: ExtremeNamedGearSetRealization,
    ) -> tuple[tuple[str, int, str], ...]:
        return tuple(
            sorted(
                (
                    str(row.slot),
                    int(row.set_id),
                    str(row.set_name),
                )
                for row in realization.body_jewelry_assignments
            )
        )

    @classmethod
    def validate(cls, state: ExtremeDualBarGearState) -> tuple[str, ...]:
        unresolved: list[str] = []
        if cls._shared_assignment_key(state.front) != cls._shared_assignment_key(state.back):
            unresolved.append(
                "Front/back Extreme named-gear witnesses disagree on shared body/jewelry assignments"
            )
        return tuple(unresolved)

    @staticmethod
    def _apply_weapon_assignments(
        build: PlayerBuild,
        realization: ExtremeNamedGearSetRealization,
        *,
        active_bar: str,
    ) -> PlayerBuild:
        # Reuse the existing materializer, but preserve the already-established
        # shared body/jewelry state by applying only the selected realization and
        # relying on pair validation to prove both snapshots agree there.
        return ExtremeNamedGearBuildMaterializerService.materialize(
            build,
            realization,
            active_bar=active_bar,
        )

    @classmethod
    def materialize(
        cls,
        build: PlayerBuild,
        state: ExtremeDualBarGearState,
    ) -> PlayerBuild:
        unresolved = cls.validate(state)
        if unresolved:
            raise ValueError(unresolved[0])

        # Materialize front first, then back. Because both witnesses have already
        # been proven to share identical body/jewelry assignments, the second pass
        # rewrites those shared slots to the same values while preserving the
        # front-bar weapons written by the first pass.
        candidate = cls._apply_weapon_assignments(build, state.front, active_bar="front")
        candidate = cls._apply_weapon_assignments(candidate, state.back, active_bar="back")
        return candidate

    @classmethod
    def set_counts_by_bar(
        cls,
        build: PlayerBuild,
        state: ExtremeDualBarGearState,
    ) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]]:
        candidate = cls.materialize(build, state)
        front = tuple(sorted(GearStatInputResolver.equipped_set_counts(candidate, active_bar="front").items()))
        back = tuple(sorted(GearStatInputResolver.equipped_set_counts(candidate, active_bar="back").items()))
        return front, back
