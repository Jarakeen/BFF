from __future__ import annotations

"""Build the finite full two-bar legality denominator for Extreme named gear.

The named gear catalog currently enumerates active-snapshot realizations.  Static
snapshot objectives do not need to rescore every compatible inactive-bar weapon
permutation, but an active snapshot is admissible only when at least one complete
front/back build can contain it.

This service groups realizations by their shared body/jewelry assignment and pairs
only snapshots that agree on that shared equipment.  The resulting pair catalog is
therefore a legality denominator, not another gear-stat implementation.  Bar-local
set activation remains owned by ``GearStatInputResolver`` through
``ExtremeDualBarGearStateService``.
"""

from dataclasses import dataclass

from services.extreme_dual_bar_gear_state_service import (
    ExtremeDualBarGearState,
    ExtremeDualBarGearStateService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
)


@dataclass(frozen=True)
class ExtremeDualBarGearStateCatalog:
    states: tuple[ExtremeDualBarGearState, ...]
    active_snapshots_reviewed: int
    compatible_pairs_reviewed: int
    unresolved: tuple[str, ...] = ()
    source_denominator_proven: bool = False

    @property
    def denominator_proven(self) -> bool:
        return bool(self.states) and self.source_denominator_proven and not self.unresolved

    def admissible_realizations(self, *, active_bar: str) -> tuple[ExtremeNamedGearSetRealization, ...]:
        bar = str(active_bar or "front").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError(f"unsupported active bar for Extreme dual-bar gear catalog: {active_bar!r}")
        rows = (state.front if bar == "front" else state.back for state in self.states)
        unique: dict[tuple[object, ...], ExtremeNamedGearSetRealization] = {}
        for row in rows:
            identity = ExtremeDualBarGearStateCatalogService.realization_identity(row)
            unique.setdefault(identity, row)
        return tuple(unique[key] for key in sorted(unique))


class ExtremeDualBarGearStateCatalogService:
    """Pair active-snapshot realizations into complete legal two-bar states."""

    @staticmethod
    def realization_identity(realization: ExtremeNamedGearSetRealization) -> tuple[object, ...]:
        return (
            tuple(realization.set_ids),
            tuple(realization.counts),
            realization.weapon_shape.value,
            tuple(
                (str(row.slot), int(row.set_id), str(row.set_name), str(row.weapon_type))
                for row in realization.assignments
            ),
        )

    @staticmethod
    def _shared_key(realization: ExtremeNamedGearSetRealization) -> tuple[tuple[str, int, str], ...]:
        return tuple(
            sorted(
                (str(row.slot), int(row.set_id), str(row.set_name))
                for row in realization.body_jewelry_assignments
            )
        )

    @classmethod
    def build(
        cls,
        realizations: tuple[ExtremeNamedGearSetRealization, ...],
        *,
        source_denominator_proven: bool,
        unresolved: tuple[str, ...] = (),
    ) -> ExtremeDualBarGearStateCatalog:
        unique: dict[tuple[object, ...], ExtremeNamedGearSetRealization] = {}
        for realization in realizations:
            unique.setdefault(cls.realization_identity(realization), realization)
        rows = tuple(unique[key] for key in sorted(unique))

        grouped: dict[tuple[tuple[str, int, str], ...], list[ExtremeNamedGearSetRealization]] = {}
        for realization in rows:
            grouped.setdefault(cls._shared_key(realization), []).append(realization)

        states: list[ExtremeDualBarGearState] = []
        pairs_reviewed = 0
        local_unresolved = list(unresolved)
        for shared_key in sorted(grouped):
            group = tuple(sorted(grouped[shared_key], key=cls.realization_identity))
            for front in group:
                for back in group:
                    pairs_reviewed += 1
                    state = ExtremeDualBarGearState(front=front, back=back)
                    errors = ExtremeDualBarGearStateService.validate(state)
                    if errors:
                        local_unresolved.extend(errors)
                        continue
                    states.append(state)

        states.sort(
            key=lambda state: (
                cls.realization_identity(state.front),
                cls.realization_identity(state.back),
            )
        )
        return ExtremeDualBarGearStateCatalog(
            states=tuple(states),
            active_snapshots_reviewed=len(rows),
            compatible_pairs_reviewed=pairs_reviewed,
            unresolved=tuple(dict.fromkeys(item for item in local_unresolved if item)),
            source_denominator_proven=bool(source_denominator_proven),
        )
