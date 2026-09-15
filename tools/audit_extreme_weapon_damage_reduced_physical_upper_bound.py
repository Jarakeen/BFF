from __future__ import annotations

"""Reduced physical upper-bound pass for unresolved Extreme Weapon Damage gear.

This audit consumes the fully triaged semantic breakpoint pool after the four remaining
blocker categories have finite bounds or an exact execution path. It deliberately does
NOT resurrect the old 60k unresolved-combination review.

For ordinary bounded rows it keeps four proof dimensions separate:

* flat Weapon Damage ceiling;
* percentage Weapon Damage ceiling;
* reviewed Max Magicka contribution;
* reviewed Max Stamina contribution.

Rows are Pareto-reduced at the semantic layer before physical slot realization. Exact
physical witnesses are then produced only from that reduced pool. Each realized witness
is scored with an intentionally favorable whole-build ceiling: the reviewed non-gear
Weapon Damage subtotal, six-slot pure-Sorcerer Expert Mage, the global 108,319 higher-
resource ceiling for Font of Power + Calculated Defense, and any bounded gear percentage.
Gear percentage is compounded separately from Class Mastery, which is at least as
favorable as the ordinary additive interpretation and therefore safe for pruning.

Twice-Born Star is never flattened. Any physical state containing its 5-piece breakpoint
is retained as an exact-execution survivor for the canonical two-Mundus evaluator.

This is a dominance reducer, not the final record scorer. A state below the incumbent
under this optimistic ceiling is safely pruned; a surviving state merely earns exact
same-build evaluation.
"""

from dataclasses import dataclass, replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.character_build.character_class import CharacterClass
from minmax.gear_set_repository import GearSetRepository
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService
from services.extreme_gear_set_power_upper_bound_service import (
    ExtremeGearSetPowerUpperBoundService,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from tools.audit_extreme_weapon_damage_four_semantic_blockers import (
    BALORGH_STATIC_ONE_PIECE,
    HEARTLAND_STATIC_TWO_PIECE,
    MAX_STORED_ULTIMATE,
    OAKFATHER_PER_MINOR_BUFF,
    OAKFATHER_STATIC_TWO_TO_FOUR,
    _minor_effect_names,
    _reviewed_dual_wield_nirnhoned_delta,
)
from tools.audit_extreme_weapon_damage_joint_named_gear_frontier import (
    _JointBreakpoint,
    _joint_rows,
)
from tools.audit_extreme_weapon_damage_joint_named_gear_realization import (
    _filtered_breakpoints,
    _filtered_eligibility,
    _filtered_topologies,
)
from tools.audit_extreme_weapon_damage_physical_gear_resource_requirements import (
    _nongear_preclass_weapon_damage,
)
from services.extreme_subclass_slot_allocation_service import (
    ExtremeSubclassSlotAllocationService,
)

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "weapon_damage"
RESOLVED_INCUMBENT = 9451.238
GLOBAL_HIGHER_RESOURCE_CEILING = 108319.0
TWICE_BORN_STAR = "Twice-Born Star"


@dataclass(frozen=True)
class _BoundedBreakpoint:
    row: _JointBreakpoint
    flat: float
    percent: float
    exact_execution_required: bool = False
    assumptions: tuple[str, ...] = ()

    @property
    def key(self) -> tuple[int, int]:
        return (int(self.row.set_id), int(self.row.piece_count))


@dataclass(frozen=True)
class _PhysicalBound:
    set_names: tuple[str, ...]
    set_ids: tuple[int, ...]
    counts: tuple[int, ...]
    topology_signature: str
    weapon_shape: str
    flat: float
    percent: float
    max_magicka: float
    max_stamina: float
    optimistic_final: float
    exact_execution_required: bool

    @property
    def higher_resource_delta(self) -> float:
        return max(self.max_magicka, self.max_stamina)

    @property
    def signature(self) -> tuple:
        return (self.set_ids, self.counts, self.weapon_shape)


def _weapon_evidence_map(catalogs):
    return {
        (int(row.set_id), int(row.piece_count)): row
        for row in catalogs[OBJECTIVE].evidence
    }


def _semantic_bound(joint: _JointBreakpoint, evidence) -> _BoundedBreakpoint:
    name = str(joint.set_name)
    count = int(joint.piece_count)

    if name == TWICE_BORN_STAR and count == 5:
        return _BoundedBreakpoint(
            row=joint,
            flat=float(joint.weapon_damage),
            percent=0.0,
            exact_execution_required=True,
            assumptions=("canonical finite two-Mundus execution required",),
        )

    if name == "Balorgh" and count == 2:
        return _BoundedBreakpoint(
            row=joint,
            flat=BALORGH_STATIC_ONE_PIECE + MAX_STORED_ULTIMATE,
            percent=0.0,
            assumptions=("all 500 stored Ultimate consumed",),
        )

    if name == "Heartland Conqueror" and count == 5:
        return _BoundedBreakpoint(
            row=joint,
            flat=HEARTLAND_STATIC_TWO_PIECE + _reviewed_dual_wield_nirnhoned_delta(),
            percent=0.0,
            assumptions=("100% trait effectiveness over proven Dual Wield Nirnhoned topology",),
        )

    if name == "Oakfather's Retribution" and count == 5:
        minor_count = len(_minor_effect_names())
        return _BoundedBreakpoint(
            row=joint,
            flat=OAKFATHER_STATIC_TWO_TO_FOUR + OAKFATHER_PER_MINOR_BUFF * float(minor_count),
            percent=0.0,
            assumptions=(f"all {minor_count} distinct catalogued Minor effects active",),
        )

    if not joint.unresolved:
        return _BoundedBreakpoint(
            row=joint,
            flat=float(joint.weapon_damage),
            percent=0.0,
        )

    flat = 0.0
    percent = 0.0
    assumptions: list[str] = []
    blockers: list[str] = []
    for bonus in evidence.candidate.source_bonuses:
        bound = ExtremeGearSetPowerUpperBoundService.build(
            str(bonus.description or ""),
            OBJECTIVE,
        )
        flat += float(bound.flat_upper_bound)
        percent += float(bound.percent_upper_bound)
        assumptions.extend(bound.assumptions)
        blockers.extend(bound.unresolved)

    if blockers:
        raise RuntimeError(
            f"Semantic blocker unexpectedly survived triage for {name} {count}pc: {tuple(blockers)!r}"
        )

    return _BoundedBreakpoint(
        row=joint,
        flat=float(flat),
        percent=float(percent),
        assumptions=tuple(dict.fromkeys(str(item) for item in assumptions if str(item))),
    )


def _dominates(left: _BoundedBreakpoint, right: _BoundedBreakpoint) -> bool:
    # Exact-execution rows are never semantically pruned by flattened rows.
    if right.exact_execution_required:
        return False
    if left.exact_execution_required:
        return False
    ge = (
        left.flat >= right.flat - 1e-9
        and left.percent >= right.percent - 1e-12
        and left.row.max_magicka >= right.row.max_magicka - 1e-9
        and left.row.max_stamina >= right.row.max_stamina - 1e-9
    )
    gt = (
        left.flat > right.flat + 1e-9
        or left.percent > right.percent + 1e-12
        or left.row.max_magicka > right.row.max_magicka + 1e-9
        or left.row.max_stamina > right.row.max_stamina + 1e-9
    )
    return ge and gt


def _semantic_pareto(rows: tuple[_BoundedBreakpoint, ...]) -> tuple[_BoundedBreakpoint, ...]:
    kept = tuple(
        row
        for row in rows
        if row.exact_execution_required
        or not any(other is not row and _dominates(other, row) for other in rows)
    )
    return tuple(
        sorted(
            kept,
            key=lambda item: (
                item.exact_execution_required is False,
                -item.flat,
                -item.percent,
                -max(item.row.max_magicka, item.row.max_stamina),
                item.row.set_name.casefold(),
                item.row.piece_count,
            ),
        )
    )


def _joint_row_map(rows: tuple[_BoundedBreakpoint, ...]) -> dict[tuple[int, int], _JointBreakpoint]:
    return {row.key: row.row for row in rows}


def _mastery_percent_ceiling() -> float:
    service = ExtremeClassMasteryPairService(DATABASE)
    result = service.best_for_class(
        CharacterClass.SORCERER,
        OBJECTIVE,
        reference_value=1.0,
        higher_max_resource=GLOBAL_HIGHER_RESOURCE_CEILING,
    )
    if result is None:
        raise RuntimeError("Sorcerer Class Mastery ceiling unavailable")
    return float(result.percent)


def _expert_mage_delta() -> float:
    result = ExtremeSubclassSlotAllocationService.best_allocation(
        ("daedric_summoning", "dark_magic", "storm_calling"),
        OBJECTIVE,
        reference_value=0.0,
    )
    if result is None:
        raise RuntimeError("Expert Mage allocation unavailable")
    return float(result.projected_delta)


def _score_physical(
    witness,
    bounded_by_key: dict[tuple[int, int], _BoundedBreakpoint],
    *,
    nongear: float,
    expert_mage: float,
    mastery_percent: float,
) -> _PhysicalBound:
    flat = 0.0
    percent = 0.0
    max_magicka = 0.0
    max_stamina = 0.0
    exact = False

    for set_id, count in zip(witness.set_ids, witness.counts):
        row = bounded_by_key.get((int(set_id), int(count)))
        if row is None:
            raise RuntimeError(f"Physical witness contains missing reduced breakpoint {(set_id, count)!r}")
        flat += float(row.flat)
        percent += float(row.percent)
        max_magicka += float(row.row.max_magicka)
        max_stamina += float(row.row.max_stamina)
        exact = exact or bool(row.exact_execution_required)

    base = float(nongear) + float(flat) + float(expert_mage)
    # Deliberately compound the independent percentage ceilings. This is more favorable
    # than ordinary additive sheet-power stacking and is therefore safe for pruning.
    optimistic = base * (1.0 + float(mastery_percent)) * (1.0 + float(percent))

    return _PhysicalBound(
        set_names=tuple(str(value) for value in witness.set_names),
        set_ids=tuple(int(value) for value in witness.set_ids),
        counts=tuple(int(value) for value in witness.counts),
        topology_signature=str(witness.topology_signature),
        weapon_shape=str(getattr(witness.weapon_shape, "value", witness.weapon_shape)),
        flat=float(flat),
        percent=float(percent),
        max_magicka=float(max_magicka),
        max_stamina=float(max_stamina),
        optimistic_final=float(optimistic),
        exact_execution_required=exact,
    )


def main() -> int:
    repository = GearSetRepository(DATABASE)
    original_breakpoints, catalogs, joint_rows = _joint_rows(repository)
    weapon_map = _weapon_evidence_map(catalogs)

    bounded: list[_BoundedBreakpoint] = []
    for joint in joint_rows:
        # Preserve the already-useful mechanic-complete Pareto candidates and every
        # unresolved row that now has a semantic bound/exact execution path. Objective-
        # irrelevant complete rows do not need to enter the challenger pool.
        if not joint.unresolved and not joint.has_positive_joint_value:
            continue
        evidence = weapon_map.get((int(joint.set_id), int(joint.piece_count)))
        if evidence is None:
            continue
        bounded.append(_semantic_bound(joint, evidence))

    bounded_rows = tuple(bounded)
    reduced = _semantic_pareto(bounded_rows)
    reduced_joint = _joint_row_map(reduced)

    breakpoints = _filtered_breakpoints(original_breakpoints, reduced_joint)
    eligibility = _filtered_eligibility(reduced_joint)
    topologies = _filtered_topologies(repository, breakpoints)
    realization_service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    )

    bounded_by_key = {row.key: row for row in reduced}
    nongear, _components = _nongear_preclass_weapon_damage()
    expert_mage = _expert_mage_delta()
    mastery_percent = _mastery_percent_ceiling()

    physical: list[_PhysicalBound] = []
    assignments_considered = 0
    assignments_rejected = 0
    for topology in topologies.topologies:
        result = realization_service.realize_topology(topology)
        assignments_considered += int(result.assignments_considered)
        assignments_rejected += int(result.assignments_rejected)
        for witness in result.realizations:
            physical.append(
                _score_physical(
                    witness,
                    bounded_by_key,
                    nongear=nongear,
                    expert_mage=expert_mage,
                    mastery_percent=mastery_percent,
                )
            )

    rows = tuple(physical)
    ordinary = tuple(row for row in rows if not row.exact_execution_required)
    tbs = tuple(row for row in rows if row.exact_execution_required)
    challengers = tuple(
        sorted(
            (row for row in ordinary if row.optimistic_final > RESOLVED_INCUMBENT + 1e-9),
            key=lambda row: (-row.optimistic_final, row.signature),
        )
    )
    pruned = tuple(row for row in ordinary if row.optimistic_final <= RESOLVED_INCUMBENT + 1e-9)

    print("EXTREME WEAPON DAMAGE REDUCED PHYSICAL UPPER-BOUND FRONTIER")
    print(f"database={DATABASE}")
    print(f"resolved_same_build_incumbent={RESOLVED_INCUMBENT:.3f}")
    print(f"global_higher_resource_ceiling={GLOBAL_HIGHER_RESOURCE_CEILING:.3f}")
    print(f"sorcerer_mastery_percent_ceiling={mastery_percent:.6f}")
    print(f"expert_mage_delta={expert_mage:.3f}")
    print(f"nongear_preclass_weapon_damage={nongear:.3f}")
    print("gear_percent_compounded_separately_for_safe_overbound=True")
    print("twice_born_star_flattened=False")
    print()

    print("SEMANTIC REDUCTION")
    print(f"bounded_or_exact_input_breakpoints={len(bounded_rows)}")
    print(f"semantic_pareto_breakpoints={len(reduced)}")
    print(f"semantic_rows_pruned={len(bounded_rows) - len(reduced)}")
    print(f"twice_born_semantic_rows={sum(1 for row in reduced if row.exact_execution_required)}")
    print(f"candidate_topologies={len(topologies.topologies)}")
    print(f"slot_eligibility_unresolved={len(eligibility.unresolved)}")
    for message in eligibility.unresolved:
        print(f"  unresolved: {message}")
    print()

    print("PHYSICAL REDUCTION")
    print(f"assignments_considered={assignments_considered}")
    print(f"assignments_rejected={assignments_rejected}")
    print(f"physical_realizations={len(rows)}")
    print(f"ordinary_bounded_physical_states={len(ordinary)}")
    print(f"twice_born_exact_execution_states={len(tbs)}")
    print(f"ordinary_states_pruned_below_incumbent={len(pruned)}")
    print(f"ordinary_states_requiring_exact_same_build_score={len(challengers)}")
    print()

    print("ORDINARY SURVIVORS REQUIRING EXACT SAME-BUILD SCORE")
    for row in challengers[:40]:
        package = " + ".join(
            f"{name} {count}pc" for name, count in zip(row.set_names, row.counts)
        )
        print(
            f"  {package} | flat_bound={row.flat:.3f} percent_bound={row.percent:.6f} "
            f"resource_delta={row.higher_resource_delta:.3f} optimistic_final={row.optimistic_final:.3f}"
        )
    if len(challengers) > 40:
        print(f"  ... {len(challengers) - 40} additional ordinary survivors omitted")
    print()

    print("TWICE-BORN STAR EXACT-EXECUTION SURVIVORS")
    unique_tbs = {}
    for row in tbs:
        unique_tbs.setdefault(row.signature, row)
    for row in sorted(unique_tbs.values(), key=lambda item: item.signature)[:40]:
        package = " + ".join(
            f"{name} {count}pc" for name, count in zip(row.set_names, row.counts)
        )
        print(
            f"  {package} | reviewed_flat_without_second_mundus={row.flat:.3f} "
            f"resource_delta={row.higher_resource_delta:.3f}"
        )
    if len(unique_tbs) > 40:
        print(f"  ... {len(unique_tbs) - 40} additional Twice-Born states omitted")
    print()

    print("PROOF STATUS")
    reduction_ready = bool(rows) and not eligibility.unresolved
    print(f"semantic_layer_fully_bounded_or_exact=True")
    print(f"reduced_physical_upper_bound_ready={reduction_ready}")
    print(f"ordinary_exact_survivor_count={len(challengers)}")
    print(f"twice_born_exact_survivor_count={len(unique_tbs)}")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=exact-score only the ordinary upper-bound survivors through the canonical same-build Sorcerer evaluator, and exact-score only the retained Twice-Born Star physical witnesses through ExtremeTwiceBornMundusStructuralStatEvaluator; all ordinary states already below 9451.238 under the optimistic ceiling are permanently pruned"
    )
    return 0 if reduction_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
