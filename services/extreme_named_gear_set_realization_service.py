from __future__ import annotations

"""Join Extreme set-count topologies to concrete named-set equipment witnesses.

The topology catalog proves only abstract piece-count arithmetic.  The generic
physical-realization layer proves body/jewelry/weapon *shapes*.  The named-set
eligibility catalog proves which slots each canonical set can actually occupy.
This service joins those three contracts and returns a concrete legal witness for
an exact ordered tuple of distinct named sets.

No ESO stat math lives here.  This is denominator legality only.
"""

from dataclasses import dataclass
from itertools import product

from services.extreme_gear_physical_slot_realization_service import (
    ExtremeGearPhysicalRealization,
    ExtremeGearPhysicalSlotRealizationService,
    ExtremeWeaponSlotShape,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)


_BODY_JEWELRY_SLOTS = (
    "Head",
    "Shoulders",
    "Chest",
    "Hands",
    "Waist",
    "Legs",
    "Feet",
    "Necklace",
    "Ring1",
    "Ring2",
)

_ONE_HANDED_MAIN_TYPES = ("Axe", "Mace", "Sword", "Dagger")
_ONE_HANDED_OFF_TYPES = (*_ONE_HANDED_MAIN_TYPES, "Shield")
_TWO_HANDED_TYPES = (
    "Two-Handed Sword",
    "Two-Handed Axe",
    "Two-Handed Mace",
    "Bow",
    "Restoration Staff",
    "Inferno Staff",
    "Ice Staff",
    "Lightning Staff",
)


@dataclass(frozen=True)
class ExtremeNamedGearSlotAssignment:
    slot: str
    set_id: int
    set_name: str
    weapon_type: str = ""


@dataclass(frozen=True)
class ExtremeNamedGearSetRealization:
    topology_signature: str
    set_ids: tuple[int, ...]
    set_names: tuple[str, ...]
    counts: tuple[int, ...]
    weapon_shape: ExtremeWeaponSlotShape
    assignments: tuple[ExtremeNamedGearSlotAssignment, ...]

    @property
    def body_jewelry_assignments(self) -> tuple[ExtremeNamedGearSlotAssignment, ...]:
        return tuple(row for row in self.assignments if not row.weapon_type)

    @property
    def weapon_assignments(self) -> tuple[ExtremeNamedGearSlotAssignment, ...]:
        return tuple(row for row in self.assignments if row.weapon_type)


class ExtremeNamedGearSetRealizationService:
    """Prove one concrete slot witness for an exact named-set topology."""

    MYTHIC_CATEGORY = "mythic"

    @classmethod
    def _violates_global_set_legality(
        cls,
        counts: tuple[int, ...],
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> bool:
        equipped_mythics = sum(
            1
            for count, item in zip(counts, named_sets)
            if count > 0 and item.category.strip().casefold() == cls.MYTHIC_CATEGORY
        )
        return equipped_mythics > 1

    @staticmethod
    def _slot_allowed(
        eligibility: ExtremeNamedGearSetSlotEligibility,
        slot: str,
    ) -> bool:
        if slot in {"Ring1", "Ring2"}:
            return "Ring" in eligibility.jewelry_slots
        if slot == "Necklace":
            return "Necklace" in eligibility.jewelry_slots
        return slot in eligibility.armor_slots

    @classmethod
    def _body_assignments(
        cls,
        remaining_counts: tuple[int, ...],
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> tuple[ExtremeNamedGearSlotAssignment, ...] | None:
        required: list[int] = []
        for set_index, count in enumerate(remaining_counts):
            required.extend([set_index] * int(count))
        if len(required) > len(_BODY_JEWELRY_SLOTS):
            return None

        # Most constrained set-units first makes the tiny ten-slot backtracking
        # deterministic and avoids exploring obviously impossible broad sets first.
        required.sort(
            key=lambda index: (
                sum(
                    1
                    for slot in _BODY_JEWELRY_SLOTS
                    if cls._slot_allowed(named_sets[index], slot)
                ),
                named_sets[index].set_id,
            )
        )

        assignments: list[ExtremeNamedGearSlotAssignment] = []
        used_slots: set[str] = set()

        def visit(position: int) -> bool:
            if position >= len(required):
                return True
            set_index = required[position]
            eligibility = named_sets[set_index]
            for slot in _BODY_JEWELRY_SLOTS:
                if slot in used_slots or not cls._slot_allowed(eligibility, slot):
                    continue
                used_slots.add(slot)
                assignments.append(
                    ExtremeNamedGearSlotAssignment(
                        slot=slot,
                        set_id=eligibility.set_id,
                        set_name=eligibility.name,
                    )
                )
                if visit(position + 1):
                    return True
                assignments.pop()
                used_slots.remove(slot)
            return False

        if not visit(0):
            return None
        return tuple(assignments)

    @staticmethod
    def _weapon_type_options(
        realization: ExtremeGearPhysicalRealization,
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> tuple[tuple[str, ...], ...]:
        indices = realization.weapon_set_indices
        if realization.weapon_shape is ExtremeWeaponSlotShape.NONE:
            return ((),)

        if realization.weapon_shape is ExtremeWeaponSlotShape.ONE_HANDED_SINGLE:
            set_row = named_sets[indices[0]]
            return tuple(
                (weapon_type,)
                for weapon_type in _ONE_HANDED_MAIN_TYPES
                if weapon_type in set_row.weapon_types
            )

        if realization.weapon_shape is ExtremeWeaponSlotShape.TWO_HANDED:
            set_row = named_sets[indices[0]]
            return tuple(
                (weapon_type,)
                for weapon_type in _TWO_HANDED_TYPES
                if weapon_type in set_row.weapon_types
            )

        first = named_sets[indices[0]]
        second = named_sets[indices[1]]
        mains = tuple(
            weapon_type
            for weapon_type in _ONE_HANDED_MAIN_TYPES
            if weapon_type in first.weapon_types
        )
        offs = tuple(
            weapon_type
            for weapon_type in _ONE_HANDED_OFF_TYPES
            if weapon_type in second.weapon_types
        )
        return tuple(product(mains, offs))

    @staticmethod
    def _weapon_assignments(
        realization: ExtremeGearPhysicalRealization,
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
        weapon_types: tuple[str, ...],
    ) -> tuple[ExtremeNamedGearSlotAssignment, ...]:
        indices = realization.weapon_set_indices
        if realization.weapon_shape is ExtremeWeaponSlotShape.NONE:
            return ()
        if realization.weapon_shape is ExtremeWeaponSlotShape.TWO_HANDED:
            row = named_sets[indices[0]]
            return (
                ExtremeNamedGearSlotAssignment(
                    slot="Main Hand",
                    set_id=row.set_id,
                    set_name=row.name,
                    weapon_type=weapon_types[0],
                ),
            )
        if realization.weapon_shape is ExtremeWeaponSlotShape.ONE_HANDED_SINGLE:
            row = named_sets[indices[0]]
            return (
                ExtremeNamedGearSlotAssignment(
                    slot="Main Hand",
                    set_id=row.set_id,
                    set_name=row.name,
                    weapon_type=weapon_types[0],
                ),
            )

        main = named_sets[indices[0]]
        off = named_sets[indices[1]]
        return (
            ExtremeNamedGearSlotAssignment(
                slot="Main Hand",
                set_id=main.set_id,
                set_name=main.name,
                weapon_type=weapon_types[0],
            ),
            ExtremeNamedGearSlotAssignment(
                slot="Off Hand",
                set_id=off.set_id,
                set_name=off.name,
                weapon_type=weapon_types[1],
            ),
        )

    @classmethod
    def find_witness(
        cls,
        topology: ExtremeGearSetCountTopology,
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> ExtremeNamedGearSetRealization | None:
        counts = tuple(int(value) for value in topology.counts)
        if len(named_sets) != len(counts):
            return None
        set_ids = tuple(int(item.set_id) for item in named_sets)
        if len(set(set_ids)) != len(set_ids):
            return None
        if any(count < 0 or count > int(item.max_equip_count) for count, item in zip(counts, named_sets)):
            return None
        if any(count > 0 and not item.has_physical_slot_evidence for count, item in zip(counts, named_sets)):
            return None
        if cls._violates_global_set_legality(counts, named_sets):
            return None

        physical_rows = ExtremeGearPhysicalSlotRealizationService._witnesses_for_topology(topology)
        for physical in physical_rows:
            body = cls._body_assignments(physical.body_jewelry_counts, named_sets)
            if body is None:
                continue
            for weapon_types in cls._weapon_type_options(physical, named_sets):
                weapons = cls._weapon_assignments(physical, named_sets, weapon_types)
                return ExtremeNamedGearSetRealization(
                    topology_signature=topology.signature,
                    set_ids=set_ids,
                    set_names=tuple(item.name for item in named_sets),
                    counts=counts,
                    weapon_shape=physical.weapon_shape,
                    assignments=tuple((*body, *weapons)),
                )
        return None

    @classmethod
    def is_realizable(
        cls,
        topology: ExtremeGearSetCountTopology,
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> bool:
        return cls.find_witness(topology, named_sets) is not None
