from __future__ import annotations

"""Classify the special/non-flat named-gear denominator for Extreme Stamina Recovery.

The ordinary 7-Medium frontier is already closed at 1166 effective pre-percent
Recovery. This audit reuses that exact merged Recovery + Max Magicka search,
classifies every excluded pair, and reduces the remaining work to a finite set of
direct-Recovery challengers. Max-Magicka-only branches are globally capped by the
remaining Enlivening Overflow headroom.
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
from services.extreme_armor_weight_filtered_slot_eligibility_service import ExtremeArmorWeightFilteredSlotEligibilityService
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevance, ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_recovery_special_branch_service import ExtremeGearSetRecoverySpecialBranchService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_special_named_gear_branch_service import ExtremeMaxResourceSpecialNamedGearBranchService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from tools.audit_extreme_stamina_recovery_exact_enlivening_and_ordinary_gear import OBJECTIVE, RESOURCE_OBJECTIVE, STANDING_MULTIPLIER, _Search, _ordinary_flat, _pair_scores

_UNMAPPED = re.compile(r"^(?P<name>.+?) \((?P<count>\d+)\): active set bonus is not yet mechanic-mapped: (?P<description>.*)$", re.DOTALL)
BASE_ENLIVENING = 88.19328
ENLIVENING_CAP = 150.0
ORDINARY_INCUMBENT = 1166.0


@dataclass(frozen=True)
class Row:
    set_id: int
    set_name: str
    piece_count: int
    recovery_kind: str | None = None
    flat: float | None = None
    percent: float | None = None
    condition: str | None = None
    can_raise: bool = False
    max_magicka_kind: str | None = None
    max_magicka_value: float | None = None
    max_magicka_condition: str | None = None
    max_magicka_recovery_ceiling: float = 0.0
    unresolved: tuple[str, ...] = ()


def _percent(effect) -> float:
    value = float(effect.value)
    return value if effect.unit is EffectUnit.PERCENT else value * 100.0


def _mapped_recovery(evidence):
    effects = tuple(e for e in evidence.candidate.source_effects if e.stat is StatId.STAMINA_RECOVERY)
    if not effects:
        return None
    positive = tuple(e for e in effects if float(e.value) > 0.0)
    if not positive:
        return ("mapped_nonpositive", None, None, None, False, ())
    unsupported = tuple(e.operation.value for e in positive if e.operation not in {EffectOperation.ADD, EffectOperation.ADD_PERCENT})
    if unsupported:
        return (None, None, None, None, False, (f"unsupported mapped Recovery operations: {unsupported!r}",))
    flat = sum(float(e.value) for e in positive if e.operation is EffectOperation.ADD)
    percent = sum(_percent(e) for e in positive if e.operation is EffectOperation.ADD_PERCENT)
    conditions = tuple(dict.fromkeys(str(e.condition or "").strip() for e in positive if str(e.condition or "").strip()))
    kind = "mapped_conditional_bundle" if flat and percent else "mapped_conditional_percent" if percent else "mapped_conditional_flat"
    return (kind, flat or None, percent or None, ",".join(conditions) or None, True, ())


def _unmapped_recovery(evidence):
    source_rows = []
    passthrough = []
    for item in evidence.candidate.unresolved:
        match = _UNMAPPED.match(str(item))
        if match is None:
            passthrough.append(str(item))
        else:
            source_rows.append((match.group("name"), int(match.group("count")), match.group("description")))
    if not source_rows:
        return None, tuple(passthrough)
    catalog = ExtremeGearSetRecoverySpecialBranchService.build(tuple(source_rows), objective_key=OBJECTIVE)
    branch = next((row for row in catalog.branches if row.set_name.casefold() == evidence.set_name.casefold() and int(row.piece_count) == int(evidence.piece_count)), None)
    return branch, tuple(dict.fromkeys((*passthrough, *catalog.unresolved)))


def _triage(pair, *, recovery_by, magicka_by, max_service, headroom: float) -> Row:
    set_id, set_name, count = pair
    unresolved: list[str] = []
    kind = None
    flat = None
    percent = None
    condition = None
    can_raise = False
    r = recovery_by.get((int(set_id), int(count)))
    if r is not None and r.status is not ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
        mapped = _mapped_recovery(r)
        if mapped is not None:
            kind, flat, percent, condition, can_raise, errors = mapped
            unresolved.extend(errors)
        else:
            branch, errors = _unmapped_recovery(r)
            unresolved.extend(errors)
            if branch is not None:
                kind = branch.kind.value
                flat = branch.flat_ceiling
                percent = branch.percent_ceiling
                condition = branch.condition or branch.search_state_rule
                can_raise = bool(branch.can_raise_self)

    mm_kind = None
    mm_value = None
    mm_condition = None
    mm_ceiling = 0.0
    m = magicka_by.get((int(set_id), int(count)))
    if m is not None and _ordinary_flat(m, RESOURCE_OBJECTIVE) is None:
        classified = max_service._classify(m)
        if isinstance(classified, str):
            if m.status is not ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
                unresolved.append(classified)
        else:
            mm_kind = classified.kind.value
            mm_value = classified.value
            mm_condition = classified.condition or (classified.search_state_rule.value if classified.search_state_rule is not None else None) or ",".join(classified.required_conditions) or None
            mm_ceiling = headroom

    if kind is None and mm_kind is None and not unresolved:
        unresolved.append("special pair has no classified Recovery or Max Magicka obligation")
    return Row(int(set_id), str(set_name), int(count), kind, flat, percent, condition, can_raise, mm_kind, mm_value, mm_condition, mm_ceiling, tuple(dict.fromkeys(unresolved)))


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def main() -> int:
    database = Path(_parser().parse_args().database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    raw = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(database, raw, required_armor_weight="Medium")
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)
    scores, merged = _pair_scores(recovery, magicka, 0.0051)
    ordinary = _Search(breakpoints=breakpoints, eligibility=filtered.catalog, relevance=merged, pair_scores=scores).search(topology)
    special_pairs = tuple(ordinary.special_or_nonflat_pairs)
    recovery_by = {(int(row.set_id), int(row.piece_count)): row for row in recovery.evidence}
    magicka_by = {(int(row.set_id), int(row.piece_count)): row for row in magicka.evidence}
    max_service = ExtremeMaxResourceSpecialNamedGearBranchService(magicka)
    headroom = max(0.0, ENLIVENING_CAP - BASE_ENLIVENING)
    rows = tuple(_triage(pair, recovery_by=recovery_by, magicka_by=magicka_by, max_service=max_service, headroom=headroom) for pair in special_pairs)

    direct = tuple(row for row in rows if row.can_raise)
    max_only = tuple(row for row in rows if not row.can_raise and row.max_magicka_kind is not None and row.max_magicka_recovery_ceiling > 0.0)
    non = tuple(row for row in rows if not row.can_raise and row.max_magicka_kind is None and not row.unresolved)
    unresolved_rows = tuple(row for row in rows if row.unresolved)

    print("EXTREME STAMINA RECOVERY SPECIAL NAMED-GEAR TRIAGE")
    print(f"database={database}")
    print(f"special_pair_count={len(special_pairs)}")
    print(f"base_enlivening={BASE_ENLIVENING:.3f}")
    print(f"remaining_enlivening_headroom={headroom:.3f}")
    print(f"ordinary_incumbent_prepercent={ORDINARY_INCUMBENT:.3f}")
    print(f"standing_multiplier={STANDING_MULTIPLIER:.6f}")
    print()
    print("CLASSIFIED SPECIAL PAIRS")
    for row in rows:
        print(f"set_id={row.set_id} set={row.set_name!r} pieces={row.piece_count} recovery_kind={row.recovery_kind!r} flat={row.flat!r} percent={row.percent!r} condition={row.condition!r} max_magicka_kind={row.max_magicka_kind!r} max_magicka_value={row.max_magicka_value!r} max_magicka_condition={row.max_magicka_condition!r} mm_recovery_ceiling={row.max_magicka_recovery_ceiling:.3f}")
        for item in row.unresolved:
            print(f"  unresolved: {item}")
    print()
    print("TRIAGE SUMMARY")
    print(f"direct_recovery_challengers={len(direct)}")
    print(f"max_magicka_only_challengers={len(max_only)}")
    print(f"reviewed_non_challengers={len(non)}")
    print(f"unresolved_pairs={len(unresolved_rows)}")
    print(f"max_magicka_only_absolute_prepercent_ceiling={headroom:.3f}")
    print(f"max_magicka_only_absolute_final_ceiling={headroom * STANDING_MULTIPLIER:.3f}")
    print("direct_challenger_names=" + repr(tuple((row.set_name, row.piece_count, row.recovery_kind, row.flat, row.percent) for row in direct)))
    print("max_magicka_only_names=" + repr(tuple((row.set_name, row.piece_count, row.max_magicka_kind) for row in max_only)))
    print()
    closed = bool(filtered.denominator_proven and ordinary.ordinary_denominator_proven and special_pairs and not unresolved_rows)
    print("PROOF GATES")
    print(f"medium_armor_physical_filter_proven={filtered.denominator_proven}")
    print(f"ordinary_denominator_prerequisite_proven={ordinary.ordinary_denominator_proven}")
    print(f"all_special_pairs_classified={not unresolved_rows}")
    print(f"special_named_gear_triage_closed={closed}")
    print("NEXT_STEP=constrained-search only the direct Recovery challengers; Max-Magicka-only branches share a global 61.807 Enlivening ceiling")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
