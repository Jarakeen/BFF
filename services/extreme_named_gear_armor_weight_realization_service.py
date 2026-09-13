from __future__ import annotations

"""Prove named-set realizations under an explicit armor-weight requirement.

The ordinary named-set realization layer proves exact slot coexistence but does not
retain ``gear_set_piece.armor_type``.  This service adds that one missing physical
dimension without redefining ordinary realization: it reuses the same topology,
named-slot eligibility, and weapon legality, then requires every named-set armor
piece used by the witness to support the requested canonical armor weight.

The database is opened read-only.  Unassigned armor slots remain caller-owned and
may be filled by ordinary non-set pieces of the requested weight.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from services.extreme_gear_physical_slot_realization_service import (
    ExtremeGearPhysicalRealization,
    ExtremeGearPhysicalSlotRealizationService,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSetRealizationService,
    ExtremeNamedGearSlotAssignment,
    _BODY_JEWELRY_SLOTS,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)
from services.stickerbook_service import EQUIP_TYPES


_ARMOR_WEIGHT_LABELS = {
    1: "Light",
    2: "Medium",
    3: "Heavy",
}
_ARMOR_SLOTS = frozenset({
    "Head",
    "Shoulders",
    "Chest",
    "Hands",
    "Waist",
    "Legs",
    "Feet",
})


@dataclass(frozen=True)
class ExtremeNamedGearArmorWeightRealizationResult:
    required_armor_weight: str
    witness: ExtremeNamedGearSetRealization | None
    unresolved: tuple[str, ...] = ()

    @property
    def compatible(self) -> bool:
        return self.witness is not None and not self.unresolved


class ExtremeNamedGearArmorWeightRealizationService:
    """Find one exact named-set witness compatible with an armor weight."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def _armor_weight_map(
        self,
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> tuple[dict[tuple[int, str], frozenset[str]], tuple[str, ...]]:
        if not self.database_path.is_file():
            return {}, (f"Armor-weight database missing: {self.database_path}",)

        set_ids = tuple(dict.fromkeys(int(row.set_id) for row in named_sets))
        if not set_ids:
            return {}, ()

        placeholders = ", ".join("?" for _ in set_ids)
        try:
            connection = sqlite3.connect(
                f"file:{self.database_path.resolve()}?mode=ro",
                uri=True,
            )
        except sqlite3.Error as exc:
            return {}, (f"Armor-weight database unreadable: {exc}",)

        weights: dict[tuple[int, str], set[str]] = {}
        unresolved: list[str] = []
        with connection:
            rows = connection.execute(
                f"""
                SELECT set_id, equip_type, COALESCE(armor_type, 0)
                FROM gear_set_piece
                WHERE set_id IN ({placeholders})
                  AND COALESCE(weapon_type, 0) = 0
                ORDER BY set_id, equip_type, armor_type
                """,
                set_ids,
            ).fetchall()

        known_set_ids = {int(row.set_id) for row in named_sets}
        seen_set_ids: set[int] = set()
        for set_id_raw, equip_raw, armor_raw in rows:
            set_id = int(set_id_raw)
            equip_id = int(equip_raw or 0)
            armor_id = int(armor_raw or 0)
            slot = EQUIP_TYPES.get(equip_id)
            if set_id not in known_set_ids or slot not in _ARMOR_SLOTS:
                continue
            seen_set_ids.add(set_id)
            label = _ARMOR_WEIGHT_LABELS.get(armor_id)
            if label is None:
                if armor_id > 0:
                    unresolved.append(
                        f"Set {set_id} slot {slot} uses unknown armor_type {armor_id}"
                    )
                continue
            weights.setdefault((set_id, slot), set()).add(label)

        for row in named_sets:
            if row.armor_slots and int(row.set_id) not in seen_set_ids:
                unresolved.append(
                    f"Set {row.name!r} has armor slots but no canonical armor-weight evidence"
                )

        return (
            {key: frozenset(value) for key, value in weights.items()},
            tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _slot_allowed(
        eligibility: ExtremeNamedGearSetSlotEligibility,
        slot: str,
        *,
        required_armor_weight: str,
        armor_weights: dict[tuple[int, str], frozenset[str]],
    ) -> bool:
        if slot in {"Ring1", "Ring2"}:
            return "Ring" in eligibility.jewelry_slots
        if slot == "Necklace":
            return "Necklace" in eligibility.jewelry_slots
        if slot not in eligibility.armor_slots:
            return False
        return required_armor_weight in armor_weights.get(
            (int(eligibility.set_id), slot),
            frozenset(),
        )

    @classmethod
    def _body_assignments(
        cls,
        physical: ExtremeGearPhysicalRealization,
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
        *,
        required_armor_weight: str,
        armor_weights: dict[tuple[int, str], frozenset[str]],
    ) -> tuple[ExtremeNamedGearSlotAssignment, ...] | None:
        required: list[int] = []
        for set_index, count in enumerate(physical.body_jewelry_counts):
            required.extend([set_index] * int(count))
        if len(required) > len(_BODY_JEWELRY_SLOTS):
            return None

        required.sort(
            key=lambda index: (
                sum(
                    1
                    for slot in _BODY_JEWELRY_SLOTS
                    if cls._slot_allowed(
                        named_sets[index],
                        slot,
                        required_armor_weight=required_armor_weight,
                        armor_weights=armor_weights,
                    )
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
                if slot in used_slots:
                    continue
                if not cls._slot_allowed(
                    eligibility,
                    slot,
                    required_armor_weight=required_armor_weight,
                    armor_weights=armor_weights,
                ):
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

        return tuple(assignments) if visit(0) else None

    def find_witness(
        self,
        topology: ExtremeGearSetCountTopology,
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
        *,
        required_armor_weight: str,
    ) -> ExtremeNamedGearArmorWeightRealizationResult:
        weight = str(required_armor_weight or "").strip().title()
        if weight not in _ARMOR_WEIGHT_LABELS.values():
            return ExtremeNamedGearArmorWeightRealizationResult(
                required_armor_weight=weight,
                witness=None,
                unresolved=(f"Unknown required armor weight: {required_armor_weight!r}",),
            )

        counts = tuple(int(value) for value in topology.counts)
        if len(named_sets) != len(counts):
            return ExtremeNamedGearArmorWeightRealizationResult(weight, None)
        set_ids = tuple(int(item.set_id) for item in named_sets)
        if len(set(set_ids)) != len(set_ids):
            return ExtremeNamedGearArmorWeightRealizationResult(weight, None)
        if any(
            count < 0 or count > int(item.max_equip_count)
            for count, item in zip(counts, named_sets)
        ):
            return ExtremeNamedGearArmorWeightRealizationResult(weight, None)
        if any(
            count > 0 and not item.has_physical_slot_evidence
            for count, item in zip(counts, named_sets)
        ):
            return ExtremeNamedGearArmorWeightRealizationResult(weight, None)
        if ExtremeNamedGearSetRealizationService._violates_global_set_legality(
            counts,
            named_sets,
        ):
            return ExtremeNamedGearArmorWeightRealizationResult(weight, None)

        armor_weights, unresolved = self._armor_weight_map(named_sets)
        if unresolved:
            return ExtremeNamedGearArmorWeightRealizationResult(
                required_armor_weight=weight,
                witness=None,
                unresolved=unresolved,
            )

        physical_rows = ExtremeGearPhysicalSlotRealizationService._witnesses_for_topology(
            topology
        )
        for physical in physical_rows:
            body = self._body_assignments(
                physical,
                named_sets,
                required_armor_weight=weight,
                armor_weights=armor_weights,
            )
            if body is None:
                continue
            for weapon_types in ExtremeNamedGearSetRealizationService._weapon_type_options(
                physical,
                named_sets,
            ):
                weapons = ExtremeNamedGearSetRealizationService._weapon_assignments(
                    physical,
                    named_sets,
                    weapon_types,
                )
                return ExtremeNamedGearArmorWeightRealizationResult(
                    required_armor_weight=weight,
                    witness=ExtremeNamedGearSetRealization(
                        topology_signature=topology.signature,
                        set_ids=set_ids,
                        set_names=tuple(item.name for item in named_sets),
                        counts=counts,
                        weapon_shape=physical.weapon_shape,
                        assignments=tuple((*body, *weapons)),
                    ),
                )

        return ExtremeNamedGearArmorWeightRealizationResult(weight, None)
