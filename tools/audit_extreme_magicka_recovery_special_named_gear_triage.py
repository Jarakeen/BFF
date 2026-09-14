from __future__ import annotations

"""Classify the special/non-flat named-gear denominator for Extreme Magicka Recovery.

The ordinary named-gear frontier is already closed.  This audit does not create a
second gear solver.  It reuses the same merged Recovery + Max Magicka denominator,
then routes every excluded pair to the canonical owner that explains why it was not
ordinary:

* direct Magicka Recovery special mechanics are classified by the shared Recovery
  special-branch semantics, with mapped conditional/percentage effects retained as
  explicit obligations;
* Max Magicka special mechanics are classified by the shared max-resource special
  branch service and bounded by the remaining Enlivening Overflow headroom.

The result is a proof-oriented triage: non-challengers can be discarded immediately,
Max-Magicka-only challengers inherit a tiny absolute Recovery ceiling from Enlivening,
and direct Recovery challengers become the finite constrained-search queue.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.effects import EffectOperation, EffectUnit
from minmax.gear_set_repository import GearSetRepository
from minmax.stat_ids import StatId
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
    ExtremeRecoverySpecialBranchKind,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialNamedGearBranchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    RECOVERY_MULTIPLIER,
    _EffectiveRecoveryOrdinarySearch,
    _ordinary_flat,
    build_pair_scores,
)
from tools.audit_extreme_magicka_recovery_armor_mundus_frontier import (
    _same_build_max_magicka_for_weight_types,
)
from tools.audit_extreme_magicka_recovery_same_build_enlivening import exact_enlivening_value

_UNMAPPED = re.compile(
    r"^(?P<name>.+?) \((?P<count>\d+)\): active set bonus is not yet mechanic-mapped: (?P<description>.*)$",
    re.DOTALL,
)


@dataclass(frozen=True)
class SpecialPairTriage:
    set_id: int
    set_name: str
    piece_count: int
    recovery_kind: str | None = None
    recovery_flat_ceiling: float | None = None
    recovery_percent_ceiling: float | None = None
    recovery_condition: str | None = None
    recovery_can_raise_self: bool = False
    max_magicka_kind: str | None = None
    max_magicka_value: float | None = None
    max_magicka_condition: str | None = None
    max_magicka_recovery_ceiling: float = 0.0
    unresolved: tuple[str, ...] = ()

    @property
    def direct_recovery_challenger(self) -> bool:
        return self.recovery_can_raise_self

    @property
    def max_magicka_only_challenger(self) -> bool:
        return (
            not self.direct_recovery_challenger
            and self.max_magicka_kind is not None
            and self.max_magicka_recovery_ceiling > 0.0
        )

    @property
    def reviewed_non_challenger(self) -> bool:
        return (
            not self.direct_recovery_challenger
            and self.max_magicka_kind is None
            and not self.unresolved
        )


def _percent_value(effect) -> float:
    value = float(effect.value)
    return value if effect.unit is EffectUnit.PERCENT else value * 100.0


def _mapped_recovery_obligation(evidence):
    effects = tuple(
        effect
        for effect in evidence.candidate.source_effects
        if effect.stat is StatId.MAGICKA_RECOVERY
    )
    if not effects:
        return None

    positive = tuple(effect for effect in effects if float(effect.value) > 0.0)
    if not positive:
        return {
            "kind": "mapped_nonpositive",
            "flat": None,
            "percent": None,
            "condition": None,
            "can_raise": False,
        }

    flat = sum(
        float(effect.value)
        for effect in positive
        if effect.operation is EffectOperation.ADD
    )
    percent = sum(
        _percent_value(effect)
        for effect in positive
        if effect.operation is EffectOperation.ADD_PERCENT
    )
    conditions = tuple(
        dict.fromkeys(
            str(effect.condition or "").strip()
            for effect in positive
            if str(effect.condition or "").strip()
        )
    )
    unsupported = tuple(
        effect.operation.value
        for effect in positive
        if effect.operation not in {EffectOperation.ADD, EffectOperation.ADD_PERCENT}
    )
    if unsupported:
        return {"unresolved": (f"unsupported mapped Recovery operations: {unsupported!r}",)}

    if flat > 0.0 and percent > 0.0:
        kind = "mapped_conditional_bundle"
    elif percent > 0.0:
        kind = "mapped_conditional_percent"
    else:
        kind = "mapped_conditional_flat"
    return {
        "kind": kind,
        "flat": flat or None,
        "percent": percent or None,
        "condition": ",".join(conditions) or None,
        "can_raise": True,
    }


def _unmapped_recovery_branch(evidence):
    rows = []
    passthrough = []
    for item in evidence.candidate.unresolved:
        match = _UNMAPPED.match(str(item))
        if match is None:
            passthrough.append(str(item))
            continue
        rows.append((match.group("name"), int(match.group("count")), match.group("description")))
    if not rows:
        return None, tuple(passthrough)
    catalog = ExtremeGearSetRecoverySpecialBranchService.build(
        tuple(rows),
        objective_key=OBJECTIVE,
    )
    branch = next(
        (
            row for row in catalog.branches
            if row.set_name.casefold() == evidence.set_name.casefold()
            and int(row.piece_count) == int(evidence.piece_count)
        ),
        None,
    )
    return branch, tuple(dict.fromkeys((*passthrough, *catalog.unresolved)))


def _triage_pair(
    pair,
    *,
    recovery_by,
    magicka_by,
    max_magicka_service,
    remaining_enlivening_headroom: float,
) -> SpecialPairTriage:
    set_id, set_name, piece_count = pair
    unresolved: list[str] = []
    recovery_kind = None
    recovery_flat = None
    recovery_percent = None
    recovery_condition = None
    recovery_can_raise = False

    recovery_evidence = recovery_by.get((int(set_id), int(piece_count)))
    if recovery_evidence is not None and recovery_evidence.status is not ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
        mapped = _mapped_recovery_obligation(recovery_evidence)
        if mapped is not None:
            unresolved.extend(mapped.get("unresolved", ()))
            if not mapped.get("unresolved"):
                recovery_kind = str(mapped["kind"])
                recovery_flat = mapped["flat"]
                recovery_percent = mapped["percent"]
                recovery_condition = mapped["condition"]
                recovery_can_raise = bool(mapped["can_raise"])
        else:
            branch, branch_unresolved = _unmapped_recovery_branch(recovery_evidence)
            unresolved.extend(branch_unresolved)
            if branch is not None:
                recovery_kind = branch.kind.value
                recovery_flat = branch.flat_ceiling
                recovery_percent = branch.percent_ceiling
                recovery_condition = branch.condition or branch.search_state_rule
                recovery_can_raise = bool(branch.can_raise_self)

    max_kind = None
    max_value = None
    max_condition = None
    max_recovery_ceiling = 0.0
    magicka_evidence = magicka_by.get((int(set_id), int(piece_count)))
    if magicka_evidence is not None and _ordinary_flat(magicka_evidence, RESOURCE_OBJECTIVE) is None:
        classified = max_magicka_service._classify(magicka_evidence)
        if isinstance(classified, str):
            if magicka_evidence.status is not ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
                unresolved.append(classified)
        else:
            max_kind = classified.kind.value
            max_value = classified.value
            max_condition = (
                classified.condition
                or (classified.search_state_rule.value if classified.search_state_rule is not None else None)
                or ",".join(classified.required_conditions)
                or None
            )
            # Any Max-Magicka-only mechanic can improve Recovery only through Enlivening.
            # The exact current headroom is therefore a global absolute ceiling even for
            # percentage/resource-state branches whose Max Magicka value is not yet scored.
            max_recovery_ceiling = float(remaining_enlivening_headroom)

    if recovery_kind is None and max_kind is None and not unresolved:
        # A pair can be excluded from the merged ordinary search because one side was
        # relevance-unresolved even when the other side is harmless. Keep that visible.
        unresolved.append("special pair has no classified Recovery or Max Magicka obligation")

    return SpecialPairTriage(
        set_id=int(set_id),
        set_name=str(set_name),
        piece_count=int(piece_count),
        recovery_kind=recovery_kind,
        recovery_flat_ceiling=recovery_flat,
        recovery_percent_ceiling=recovery_percent,
        recovery_condition=recovery_condition,
        recovery_can_raise_self=recovery_can_raise,
        max_magicka_kind=max_kind,
        max_magicka_value=max_value,
        max_magicka_condition=max_condition,
        max_magicka_recovery_ceiling=max_recovery_ceiling,
        unresolved=tuple(dict.fromkeys(unresolved)),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def main() -> int:
    database = Path(_parser().parse_args().database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    raw_eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database,
        raw_eligibility,
        required_armor_weight="Light",
    )

    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    max_magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)

    base_max_magicka, max_magicka_unresolved = _same_build_max_magicka_for_weight_types(database, 1)
    base_enlivening = exact_enlivening_value(base_max_magicka)
    remaining_headroom = max(0.0, 150.0 - base_enlivening)
    conversion = 0.0051

    pair_scores, merged = build_pair_scores(
        recovery,
        max_magicka,
        max_magicka_to_recovery=conversion,
    )
    ordinary_search = _EffectiveRecoveryOrdinarySearch(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=merged,
        pair_scores=pair_scores,
    ).search(topology)
    special_pairs = tuple(ordinary_search.special_or_nonflat_pairs)

    recovery_by = {(int(row.set_id), int(row.piece_count)): row for row in recovery.evidence}
    magicka_by = {(int(row.set_id), int(row.piece_count)): row for row in max_magicka.evidence}
    max_magicka_service = ExtremeMaxResourceSpecialNamedGearBranchService(max_magicka)

    rows = tuple(
        _triage_pair(
            pair,
            recovery_by=recovery_by,
            magicka_by=magicka_by,
            max_magicka_service=max_magicka_service,
            remaining_enlivening_headroom=remaining_headroom,
        )
        for pair in special_pairs
    )

    direct = tuple(row for row in rows if row.direct_recovery_challenger)
    max_only = tuple(row for row in rows if row.max_magicka_only_challenger)
    non_challengers = tuple(row for row in rows if row.reviewed_non_challenger)
    unresolved_rows = tuple(row for row in rows if row.unresolved)
    classified_count = len(rows) - len(unresolved_rows)

    print("EXTREME MAGICKA RECOVERY SPECIAL NAMED-GEAR TRIAGE")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print(f"special_pair_count={len(special_pairs)}")
    print(f"same_build_max_magicka_before_named_gear={base_max_magicka:.3f}")
    print(f"base_enlivening={base_enlivening:.3f}")
    print(f"remaining_enlivening_headroom={remaining_headroom:.3f}")
    print(f"locked_recovery_multiplier={RECOVERY_MULTIPLIER:.6f}")
    print()

    print("CLASSIFIED SPECIAL PAIRS")
    for row in rows:
        print(
            f"set_id={row.set_id} set={row.set_name!r} pieces={row.piece_count} "
            f"recovery_kind={row.recovery_kind!r} recovery_flat_ceiling={row.recovery_flat_ceiling!r} "
            f"recovery_percent_ceiling={row.recovery_percent_ceiling!r} recovery_condition={row.recovery_condition!r} "
            f"max_magicka_kind={row.max_magicka_kind!r} max_magicka_value={row.max_magicka_value!r} "
            f"max_magicka_condition={row.max_magicka_condition!r} "
            f"max_magicka_recovery_ceiling={row.max_magicka_recovery_ceiling:.3f}"
        )
        for item in row.unresolved:
            print(f"  unresolved: {item}")
    print()

    print("TRIAGE SUMMARY")
    print(f"classified_pairs={classified_count}")
    print(f"direct_recovery_challengers={len(direct)}")
    print(f"max_magicka_only_challengers={len(max_only)}")
    print(f"reviewed_non_challengers={len(non_challengers)}")
    print(f"unresolved_pairs={len(unresolved_rows)}")
    print(f"max_magicka_only_absolute_prepercent_recovery_ceiling={remaining_headroom:.3f}")
    print(f"max_magicka_only_absolute_final_recovery_ceiling={remaining_headroom * RECOVERY_MULTIPLIER:.3f}")
    print(f"max_magicka_witness_unresolved_count={len(max_magicka_unresolved)}")
    for item in max_magicka_unresolved:
        print(f"  unresolved: {item}")
    print()

    classified = bool(
        filtered.denominator_proven
        and ordinary_search.ordinary_denominator_proven
        and special_pairs
        and not unresolved_rows
        and not max_magicka_unresolved
    )
    print("PROOF GATES")
    print(f"light_armor_physical_filter_proven={filtered.denominator_proven}")
    print(f"ordinary_denominator_prerequisite_proven={ordinary_search.ordinary_denominator_proven}")
    print(f"all_special_pairs_classified={not unresolved_rows}")
    print(f"special_named_gear_triage_closed={classified}")
    if classified:
        print(
            "NEXT_STEP=run constrained physical searches for direct-Recovery challengers and "
            "Max-Magicka-only challengers using the ordinary 1332 Recovery winner as the dominance target"
        )
    else:
        print("NEXT_STEP=close only the reported special-pair classification gaps")
    return 0 if classified else 2


if __name__ == "__main__":
    raise SystemExit(main())
