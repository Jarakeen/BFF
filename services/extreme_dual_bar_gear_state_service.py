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
    def shared_assignment_key(
        realization: ExtremeNamedGearSetRealization,
    ) -> tuple[tuple[str, int, str], ...]:
        body_rows = getattr(realization, "body_jewelry_assignments", None)
        if body_rows is None:
            body_rows = tuple(
                row
                for row in getattr(realization, "assignments", ())
                if not str(getattr(row, "weapon_type", "") or "").strip()
            )
        return tuple(
            sorted(
                (
                    str(row.slot),
                    int(row.set_id),
                    str(row.set_name),
                )
                for row in body_rows
            )
        )

    @classmethod
    def validate(cls, state: ExtremeDualBarGearState) -> tuple[str, ...]:
        unresolved: list[str] = []
        if cls.shared_assignment_key(state.front) != cls.shared_assignment_key(state.back):
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
