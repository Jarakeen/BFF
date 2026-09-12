from __future__ import annotations

"""Proof-safe structural reuse for Max Resource special-subset filler searches.

Special mechanics are executed later by their canonical owners.  The subset search
here optimizes only the ordinary exact-flat filler around fixed special identities.
Two subset searches may therefore share that filler result only when they expose the
same topology, special breakpoint multiset, physical eligibility shapes, and any
special identities that overlap an ordinary candidate domain.

Reuse never trusts a copied slot assignment.  Target special identities are mapped
onto the representative ordered set tuple and the canonical named-gear realizer must
prove a fresh witness.  Any ambiguity or failed witness returns ``None`` so callers
fall back to the full exact search.
"""

from collections import defaultdict
from typing import Iterable

from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_max_health_named_gear_candidate_search_service import (
    ExtremeMaxHealthSpecialSubsetSearchStats,
    ExtremeMaxHealthSpecialSubsetWinner,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)


class ExtremeMaxResourceSpecialSubsetEquivalenceService:
    """Classify and rematerialize structurally equivalent special-subset searches."""

    @staticmethod
    def _physical_shape(row: ExtremeNamedGearSetSlotEligibility) -> tuple[object, ...]:
        return (
            str(row.category or "").strip().casefold(),
            int(row.max_equip_count),
            tuple(row.armor_slots),
            tuple(row.jewelry_slots),
            tuple(row.weapon_types),
            tuple(int(value) for value in row.other_equip_types),
        )

    @classmethod
    def _branch_group_key(
        cls,
        branch,
        eligibility_by_id: dict[int, ExtremeNamedGearSetSlotEligibility],
    ) -> tuple[object, ...] | None:
        physical = eligibility_by_id.get(int(branch.set_id))
        if physical is None or not physical.has_physical_slot_evidence:
            return None
        return (int(branch.piece_count), cls._physical_shape(physical))

    @classmethod
    def structural_key(
        cls,
        *,
        topology: ExtremeGearSetCountTopology,
        subset: tuple[object, ...],
        ordinary_candidates_by_count,
        eligibility_by_id: dict[int, ExtremeNamedGearSetSlotEligibility],
    ) -> tuple[object, ...] | None:
        special_shapes: list[tuple[object, ...]] = []
        ordinary_domain_exclusions: list[tuple[int, tuple[int, ...]]] = []

        ordinary_ids_by_count = {
            int(count): frozenset(int(row.set_id) for row in rows)
            for count, rows in ordinary_candidates_by_count.items()
        }
        exclusions: dict[int, list[int]] = defaultdict(list)

        for branch in subset:
            group_key = cls._branch_group_key(branch, eligibility_by_id)
            if group_key is None:
                return None
            special_shapes.append(group_key)
            count = int(branch.piece_count)
            set_id = int(branch.set_id)
            if set_id in ordinary_ids_by_count.get(count, frozenset()):
                exclusions[count].append(set_id)

        for count, ids in sorted(exclusions.items()):
            ordinary_domain_exclusions.append((count, tuple(sorted(ids))))

        return (
            tuple(int(value) for value in topology.counts),
            int(topology.unused_units),
            tuple(sorted(special_shapes, key=repr)),
            tuple(ordinary_domain_exclusions),
        )

    @classmethod
    def _special_id_mapping(
        cls,
        *,
        representative_subset: tuple[object, ...],
        target_subset: tuple[object, ...],
        eligibility_by_id: dict[int, ExtremeNamedGearSetSlotEligibility],
    ) -> dict[int, int] | None:
        representative_groups: dict[tuple[object, ...], list[object]] = defaultdict(list)
        target_groups: dict[tuple[object, ...], list[object]] = defaultdict(list)

        for branch in representative_subset:
            key = cls._branch_group_key(branch, eligibility_by_id)
            if key is None:
                return None
            representative_groups[key].append(branch)
        for branch in target_subset:
            key = cls._branch_group_key(branch, eligibility_by_id)
            if key is None:
                return None
            target_groups[key].append(branch)

        if set(representative_groups) != set(target_groups):
            return None

        mapping: dict[int, int] = {}
        for key in representative_groups:
            source = sorted(representative_groups[key], key=lambda row: int(row.set_id))
            target = sorted(target_groups[key], key=lambda row: int(row.set_id))
            if len(source) != len(target):
                return None
            for left, right in zip(source, target):
                mapping[int(left.set_id)] = int(right.set_id)
        return mapping

    @staticmethod
    def _pairs(subset: Iterable[object]) -> tuple[tuple[int, str, int], ...]:
        return tuple(
            sorted(
                (
                    (int(row.set_id), str(row.set_name), int(row.piece_count))
                    for row in subset
                ),
                key=lambda row: (row[2], row[0], row[1].casefold()),
            )
        )

    @classmethod
    def rematerialize(
        cls,
        *,
        topology: ExtremeGearSetCountTopology,
        representative_subset: tuple[object, ...],
        representative_winner: ExtremeMaxHealthSpecialSubsetWinner,
        target_subset: tuple[object, ...],
        eligibility_by_id: dict[int, ExtremeNamedGearSetSlotEligibility],
    ) -> ExtremeMaxHealthSpecialSubsetWinner | None:
        mapping = cls._special_id_mapping(
            representative_subset=representative_subset,
            target_subset=target_subset,
            eligibility_by_id=eligibility_by_id,
        )
        if mapping is None:
            return None

        pairs = cls._pairs(target_subset)
        if not representative_winner.winner_found:
            return ExtremeMaxHealthSpecialSubsetWinner(
                topology=topology,
                special_pairs=pairs,
                best_ordinary_flat_delta=representative_winner.best_ordinary_flat_delta,
                realizations=(),
                stats=ExtremeMaxHealthSpecialSubsetSearchStats(),
            )

        realized: dict[tuple[object, ...], ExtremeNamedGearSetRealization] = {}
        for witness in representative_winner.realizations:
            mapped_ids = tuple(mapping.get(int(set_id), int(set_id)) for set_id in witness.set_ids)
            if len(set(mapped_ids)) != len(mapped_ids):
                return None
            try:
                named_sets = tuple(eligibility_by_id[int(set_id)] for set_id in mapped_ids)
            except KeyError:
                return None
            canonical = ExtremeNamedGearSetRealizationService.find_witness(topology, named_sets)
            if canonical is None:
                return None
            identity = (
                canonical.set_ids,
                canonical.counts,
                canonical.weapon_shape.value,
                tuple((row.slot, row.set_id, row.weapon_type) for row in canonical.assignments),
            )
            realized.setdefault(identity, canonical)

        if not realized:
            return None
        rows = tuple(realized[key] for key in sorted(realized))
        return ExtremeMaxHealthSpecialSubsetWinner(
            topology=topology,
            special_pairs=pairs,
            best_ordinary_flat_delta=representative_winner.best_ordinary_flat_delta,
            realizations=rows,
            stats=ExtremeMaxHealthSpecialSubsetSearchStats(
                witness_checks=len(rows),
                feasible_leaves=len(rows),
                semantic_leaf_classes=len(rows),
            ),
        )


__all__ = ["ExtremeMaxResourceSpecialSubsetEquivalenceService"]
