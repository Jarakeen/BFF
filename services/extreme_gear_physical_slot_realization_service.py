from __future__ import annotations

"""Prove generic physical slot realization for Extreme gear count topologies.

This layer answers a narrower question than named-set legality: can an abstract
set-count vector be placed onto ESO's physical active-snapshot equipment shape?
The active snapshot has ten independent body/jewelry item slots (seven armor,
three jewelry) plus a weapon shape. Weapon shapes matter because one two-handed
item contributes two set-count units to the *same* set, while paired one-handed
items contribute one unit each and may belong to different sets.

Named-set slot eligibility remains deliberately separate. A generic realization
is not evidence that a Mythic, monster piece, arena weapon, or other special set
can occupy the witness slots. Callers must keep that proof boundary visible.
"""

from dataclasses import dataclass
from enum import Enum
from itertools import product

from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)


BODY_JEWELRY_SINGLE_SLOTS = 10


class ExtremeWeaponSlotShape(str, Enum):
    NONE = "none"
    ONE_HANDED_SINGLE = "one_handed_single"
    TWO_HANDED = "two_handed"
    PAIRED_ONE_HANDED = "paired_one_handed"


@dataclass(frozen=True)
class ExtremeGearPhysicalRealization:
    topology_signature: str
    body_jewelry_counts: tuple[int, ...]
    weapon_shape: ExtremeWeaponSlotShape
    weapon_set_indices: tuple[int, ...] = ()

    @property
    def body_jewelry_units(self) -> int:
        return sum(self.body_jewelry_counts)

    @property
    def weapon_set_units(self) -> int:
        if self.weapon_shape is ExtremeWeaponSlotShape.NONE:
            return 0
        if self.weapon_shape is ExtremeWeaponSlotShape.ONE_HANDED_SINGLE:
            return 1
        return 2


@dataclass(frozen=True)
class ExtremeGearPhysicalSlotRealizationCatalog:
    realizations: tuple[ExtremeGearPhysicalRealization, ...]
    unresolved: tuple[str, ...] = ()
    named_set_slot_eligibility_proven: bool = False

    @property
    def generic_slot_shape_denominator_proven(self) -> bool:
        return bool(self.realizations) and not self.unresolved

    @property
    def physical_slot_realization_proven(self) -> bool:
        return self.generic_slot_shape_denominator_proven and self.named_set_slot_eligibility_proven


class ExtremeGearPhysicalSlotRealizationService:
    """Find deterministic physical witnesses for abstract set-count topologies."""

    @staticmethod
    def _subtract(
        counts: tuple[int, ...],
        weapon_set_indices: tuple[int, ...],
    ) -> tuple[int, ...] | None:
        remaining = list(counts)
        for index in weapon_set_indices:
            if index < 0 or index >= len(remaining) or remaining[index] <= 0:
                return None
            remaining[index] -= 1
        return tuple(remaining)

    @classmethod
    def _witnesses_for_topology(
        cls,
        topology: ExtremeGearSetCountTopology,
    ) -> tuple[ExtremeGearPhysicalRealization, ...]:
        counts = tuple(int(value) for value in topology.counts)
        rows: list[ExtremeGearPhysicalRealization] = []

        def add(shape: ExtremeWeaponSlotShape, indices: tuple[int, ...]) -> None:
            remaining = cls._subtract(counts, indices)
            if remaining is None or sum(remaining) > BODY_JEWELRY_SINGLE_SLOTS:
                return
            rows.append(
                ExtremeGearPhysicalRealization(
                    topology_signature=topology.signature,
                    body_jewelry_counts=remaining,
                    weapon_shape=shape,
                    weapon_set_indices=indices,
                )
            )

        # No equipped set-bearing weapon item. Any unused weapon capacity remains
        # part of topology.unused_units rather than being silently assigned.
        if sum(counts) <= BODY_JEWELRY_SINGLE_SLOTS:
            add(ExtremeWeaponSlotShape.NONE, ())

        # A single one-handed weapon contributes one set-count unit. ESO permits
        # an otherwise empty off-hand, so this shape is part of the legal universe.
        for index in range(len(counts)):
            add(ExtremeWeaponSlotShape.ONE_HANDED_SINGLE, (index,))

        # Paired one-handed items contribute independently and can split set
        # identities. Product, rather than combinations, also permits both pieces
        # to belong to the same set when its count is at least two.
        for first, second in product(range(len(counts)), repeat=2):
            add(ExtremeWeaponSlotShape.PAIRED_ONE_HANDED, (first, second))

        # A two-handed item is one physical item but contributes two set-count
        # units to one set identity. It cannot split those units across sets.
        for index, count in enumerate(counts):
            if count >= 2:
                add(ExtremeWeaponSlotShape.TWO_HANDED, (index, index))

        unique: dict[
            tuple[tuple[int, ...], ExtremeWeaponSlotShape, tuple[int, ...]],
            ExtremeGearPhysicalRealization,
        ] = {}
        for row in rows:
            key = (row.body_jewelry_counts, row.weapon_shape, row.weapon_set_indices)
            unique.setdefault(key, row)
        return tuple(
            sorted(
                unique.values(),
                key=lambda row: (
                    row.weapon_shape.value,
                    row.weapon_set_indices,
                    row.body_jewelry_counts,
                ),
            )
        )

    def build(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
    ) -> ExtremeGearPhysicalSlotRealizationCatalog:
        realizations: list[ExtremeGearPhysicalRealization] = []
        unresolved: list[str] = list(topology_catalog.unresolved)

        for topology in topology_catalog.topologies:
            witnesses = self._witnesses_for_topology(topology)
            if not witnesses:
                unresolved.append(
                    f"No generic physical slot realization for gear topology {topology.signature}"
                )
                continue
            realizations.extend(witnesses)

        return ExtremeGearPhysicalSlotRealizationCatalog(
            realizations=tuple(realizations),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
            named_set_slot_eligibility_proven=False,
        )
