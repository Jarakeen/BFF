from __future__ import annotations

"""Inventory proof-owned Health Recovery components before record scoring.

This is deliberately not a whole-record optimizer. It reviews direct canonical
sources that can change the Health Recovery rating and keeps every unclosed axis
explicit so a large-but-incomplete number cannot masquerade as a proven record.
"""

import argparse
from collections import Counter
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.alchemy_potion_buff_semantics import potion_buff_for_trait
from minmax.base_character_state import BASE_HEALTH_RECOVERY
from minmax.combat_effect_semantics import GameUpdate
from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository
from minmax.named_combat_buffs import effects_for_buff
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.stat_ids import StatId
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
)

OBJECTIVE = "health_recovery"
_UNRESOLVED_ROW = re.compile(
    r"^(?P<name>.+?) \((?P<count>\d+)\): active set bonus is not yet mechanic-mapped: (?P<description>.*)$",
    re.DOTALL,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _mundus_projection(repository: MundusRepository):
    rows: list[tuple[float, str]] = []
    unresolved: list[str] = []
    for raw_name in repository.list_names():
        name = str(raw_name or "").strip()
        if not name:
            continue
        records = tuple(repository.get_records(name))
        target = tuple(
            row
            for row in records
            if str(row.stat_id).strip().casefold() == StatId.HEALTH_RECOVERY.value.casefold()
        )
        for row in target:
            if not bool(row.supported):
                unresolved.append(f"unsupported Health Recovery Mundus semantics: {name}: {row.notes}")
                continue
            if str(row.unit or "").strip().casefold() != "flat":
                unresolved.append(f"non-flat Health Recovery Mundus semantics: {name}: {row.unit}")
                continue
            value = float(row.value)
            if value > 0.0:
                rows.append((value, name))
            elif value < 0.0:
                unresolved.append(f"negative Health Recovery Mundus mutation: {name}: {value}")
    rows.sort(key=lambda item: (-item[0], item[1].casefold(), item[1]))
    return tuple(rows), tuple(dict.fromkeys(unresolved))


def _provisioning_kind_map(database: Path) -> dict[str, str]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """
            SELECT lower(name), lower(trim(entity_type))
            FROM entity
            WHERE lower(trim(entity_type)) IN ('food', 'drink')
            ORDER BY lower(name), lower(trim(entity_type))
            """
        ).fetchall()
    values: dict[str, set[str]] = {}
    for raw_name, raw_kind in rows:
        name = str(raw_name or "").strip().casefold()
        kind = str(raw_kind or "").strip().casefold()
        if name and kind:
            values.setdefault(name, set()).add(kind)
    return {
        name: next(iter(kinds))
        for name, kinds in values.items()
        if len(kinds) == 1
    }


def _provisioning_projection(database: Path):
    repository = ProvisioningStaticRepository(database)
    kind_map = _provisioning_kind_map(database)
    best: dict[str, tuple[float, str] | None] = {"food": None, "drink": None}
    relevant: list[tuple[float, str, str]] = []
    unresolved: list[str] = []

    for raw_name in repository.list_names():
        name = str(raw_name or "").strip()
        if not name:
            continue
        effects, effect_unresolved = repository.resolve(name)
        target_effects = tuple(effect for effect in effects if effect.stat is StatId.HEALTH_RECOVERY)
        if target_effects:
            for message in effect_unresolved:
                unresolved.append(f"{name}: {message}")
        value = 0.0
        supported = True
        for effect in target_effects:
            if effect.operation is not EffectOperation.ADD:
                unresolved.append(
                    f"{name}: unsupported Health Recovery provisioning operation {effect.operation.value}"
                )
                supported = False
                continue
            value += float(effect.value)
        if not supported or value <= 0.0:
            continue
        kind = kind_map.get(name.casefold())
        if kind not in best:
            unresolved.append(f"{name}: no unique canonical food/drink identity")
            continue
        relevant.append((value, kind, name))
        current = best[kind]
        if current is None or value > current[0] + 1e-9 or (
            abs(value - current[0]) <= 1e-9 and (name.casefold(), name) < (current[1].casefold(), current[1])
        ):
            best[kind] = (value, name)

    relevant.sort(key=lambda row: (-row[0], row[1], row[2].casefold(), row[2]))
    return best, tuple(relevant), tuple(dict.fromkeys(unresolved)), len(repository.list_names())


def _potion_projection(database: Path):
    repository = PotionAvailabilityRepository(database, game_update=GameUpdate.U50)
    catalog = repository.catalog()
    relevant: list[tuple[str, tuple[str, ...]]] = []
    unresolved: list[str] = [str(item) for item in catalog.unresolved if str(item)]

    for formula in catalog.formulas:
        buffs: list[str] = []
        for trait in formula.traits:
            buff = potion_buff_for_trait(str(trait), game_update=GameUpdate.U50)
            if not buff:
                continue
            effects = effects_for_buff(buff, game_update=GameUpdate.U50)
            if any(effect.stat is StatId.HEALTH_RECOVERY for effect in effects):
                buffs.append(buff)
        if buffs:
            relevant.append((str(formula.canonical_id or ""), tuple(dict.fromkeys(buffs))))

    return catalog, tuple(relevant), tuple(dict.fromkeys(unresolved))


def _special_frontier(repository: GearSetRepository):
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    rows: list[tuple[str, int, str]] = []
    parse_unresolved: list[str] = []
    for item in relevance.unresolved:
        match = _UNRESOLVED_ROW.match(str(item))
        if match is None:
            parse_unresolved.append(str(item))
            continue
        rows.append((match.group("name"), int(match.group("count")), match.group("description")))
    catalog = ExtremeGearSetRecoverySpecialBranchService.build(tuple(rows), objective_key=OBJECTIVE)
    unresolved = tuple(dict.fromkeys((*parse_unresolved, *catalog.unresolved)))
    return breakpoints, relevance, catalog, unresolved


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    mundus = MundusRepository(database, initialize=False)
    mundus_rows, mundus_unresolved = _mundus_projection(mundus)
    best_provisioning, provisioning_rows, provisioning_unresolved, provisioning_reviewed = _provisioning_projection(database)
    potion_catalog, potion_relevant, potion_unresolved = _potion_projection(database)
    gear_repository = GearSetRepository(database)
    breakpoints, relevance, special, special_unresolved = _special_frontier(gear_repository)

    semantic_denominator_proven = bool(
        relevance.breakpoints_reviewed
        and not special_unresolved
        and len(relevance.unresolved) == len(special.branches)
    )
    kind_counts = Counter(row.kind.value for row in special.branches)

    print("EXTREME HEALTH RECOVERY CONSTRUCTIVE COMPONENT AUDIT")
    print(f"database={database}")
    print("mode=constructive_components_not_whole_record_search")
    print()

    print("PROVEN / DIRECT COMPONENTS")
    print(f"base_health_recovery={float(BASE_HEALTH_RECOVERY):.3f}")
    print("attribute_points_direct_delta=0.000 base_formula_attribute_points=0 base_formula_attribute_value=0.0")
    if mundus_rows:
        print(
            f"mundus={mundus_rows[0][1]!r} base_delta={mundus_rows[0][0]:.3f} "
            f"positive_health_recovery_stones={len(mundus_rows)} unresolved={len(mundus_unresolved)}"
        )
    else:
        print(f"mundus=<none> positive_health_recovery_stones=0 unresolved={len(mundus_unresolved)}")
    for kind in ("food", "drink"):
        row = best_provisioning[kind]
        if row is None:
            print(f"{kind}=<none> delta=0.000")
        else:
            print(f"{kind}={row[1]!r} delta={row[0]:.3f}")
    print(
        f"provisioning_reviewed={provisioning_reviewed} relevant_rows={len(provisioning_rows)} "
        f"unresolved={len(provisioning_unresolved)}"
    )
    print(
        f"potion_formulas_reviewed={len(potion_catalog.formulas)} "
        f"health_recovery_relevant_formulas={len(potion_relevant)} "
        f"catalog_unresolved={len(potion_unresolved)}"
    )
    for formula_id, buffs in potion_relevant[:12]:
        print(f"  potion_relevant: {formula_id or '<unnamed>'} buffs={buffs!r}")
    print("named_buff_major_fortitude=+30%")
    print("named_buff_minor_fortitude=+15%")
    print()

    print("GEAR SEMANTIC FRONTIER")
    print(f"gear_breakpoints_reviewed={relevance.breakpoints_reviewed}")
    print(f"base_relevance_denominator_proven={relevance.denominator_proven}")
    print(f"special_rows_reviewed={len(special.branches)}")
    print(f"positive_special_challengers={len(special.positive_challengers)}")
    print(f"reviewed_non_challengers={len(special.reviewed_non_challengers)}")
    print(f"semantic_special_denominator_proven={semantic_denominator_proven}")
    print("special_branch_kinds=" + ", ".join(f"{key}:{value}" for key, value in sorted(kind_counts.items())))
    for row in sorted(
        special.positive_challengers,
        key=lambda item: (-(item.flat_ceiling or 0.0), -(item.percent_ceiling or 0.0), item.set_name.casefold()),
    )[:12]:
        print(
            f"  {row.set_name} {row.piece_count}pc kind={row.kind.value} "
            f"flat_ceiling={row.flat_ceiling!r} percent_ceiling={row.percent_ceiling!r}"
        )
    print()

    unresolved: list[str] = []
    unresolved.extend(mundus_unresolved)
    unresolved.extend(provisioning_unresolved)
    unresolved.extend(special_unresolved)
    # Potion catalog parser-provenance warnings are reported above but are not yet
    # neutralized for recovery objectives; keep that axis explicitly open.
    if potion_unresolved:
        unresolved.append(
            f"Potion catalog has {len(potion_unresolved)} unresolved source warning(s) requiring recovery-specific review"
        )

    print("OPEN WHOLE-RECORD AXES")
    print("  race_projection=pending")
    print("  class_route_and_passive_projection=pending")
    print("  armor_weight_and_trait_projection=pending")
    print("  jewelry_trait_and_enchant_projection=pending")
    print("  champion_point_projection=pending")
    print("  runtime_condition_compatibility=pending")
    print("  ordinary_named_gear_exact_closure=pending")
    print("  special_named_gear_numeric_scoring=pending")
    print("  search_state_mutations_oakensoul_torc_twice_born=pending")
    print()
    print(f"direct_component_unresolved_count={len(tuple(dict.fromkeys(unresolved)))}")
    for item in tuple(dict.fromkeys(unresolved)):
        print(f"  unresolved: {item}")
    print("NEXT_STEP=proof-reduce race/class/passive and recovery equipment axes, then score the strongest legal ordinary incumbent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
