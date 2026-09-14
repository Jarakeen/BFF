from __future__ import annotations

"""Promote the exact Extreme Stamina Recovery special named-gear champion.

The special named-gear denominator has already been reduced to three live exact
challengers: Torc of Tonal Constancy, Prowler's Talisman, and Lustrous Soulwell.
This audit does not require them to lose to the prior ordinary incumbent. It scores
their exact physical structural witnesses plus exact reviewed special contributions,
then promotes the strongest legal named-gear branch as the new incumbent.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialNamedGearBranchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from tools.audit_extreme_stamina_recovery_exact_enlivening_and_ordinary_gear import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    _Search,
    _pair_scores,
)
from tools.audit_extreme_stamina_recovery_special_named_gear_exact_survivors import (
    _exact_structural,
)
from tools.audit_extreme_stamina_recovery_special_named_gear_triage import (
    BASE_ENLIVENING,
    ENLIVENING_CAP,
    ORDINARY_INCUMBENT,
    _triage,
)

TARGETS = (
    "Torc of Tonal Constancy",
    "Prowler's Talisman",
    "Lustrous Soulwell",
)
MAX_MAGICKA_TO_RECOVERY = 0.0051


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _exact_special(row, *, headroom: float) -> tuple[float | None, tuple[str, ...]]:
    unresolved: list[str] = []
    direct = float(row.flat or 0.0)
    derived = 0.0

    if row.percent is not None:
        unresolved.append(f"{row.set_name}: percentage special branch is not exact-flat comparable here")

    if row.max_magicka_kind is not None:
        if row.max_magicka_value is None:
            unresolved.append(f"{row.set_name}: Max Magicka special value unresolved")
        else:
            # The triage classifier owns the exact reviewed special Max Magicka
            # ceiling. Enlivening converts that same-build value at the already
            # proven 0.5% coefficient including the 2% Undaunted resource factor,
            # and cannot exceed the remaining global headroom.
            derived = min(float(headroom), max(0.0, float(row.max_magicka_value)) * MAX_MAGICKA_TO_RECOVERY)

    if unresolved:
        return None, tuple(dict.fromkeys(unresolved))
    return direct + derived, ()


def main() -> int:
    database = Path(_parser().parse_args().database)
    unresolved: list[str] = []

    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    raw = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database, raw, required_armor_weight="Medium"
    )
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)
    pair_scores, merged = _pair_scores(recovery, magicka, MAX_MAGICKA_TO_RECOVERY)
    ordinary = _Search(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=merged,
        pair_scores=pair_scores,
    ).search(topology)

    recovery_by = {(int(row.set_id), int(row.piece_count)): row for row in recovery.evidence}
    magicka_by = {(int(row.set_id), int(row.piece_count)): row for row in magicka.evidence}
    max_service = ExtremeMaxResourceSpecialNamedGearBranchService(magicka)
    headroom = max(0.0, ENLIVENING_CAP - BASE_ENLIVENING)
    triage = tuple(
        _triage(
            pair,
            recovery_by=recovery_by,
            magicka_by=magicka_by,
            max_service=max_service,
            headroom=headroom,
        )
        for pair in ordinary.special_or_nonflat_pairs
    )
    by_name = {row.set_name: row for row in triage}

    rows = []
    for name in TARGETS:
        challenger = by_name.get(name)
        if challenger is None:
            unresolved.append(f"missing triage row: {name}")
            continue
        unresolved.extend(f"{name}: {item}" for item in challenger.unresolved)
        structural, witness_sets, errors = _exact_structural(
            challenger=challenger,
            topology=topology,
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            merged=merged,
            pair_scores=pair_scores,
        )
        unresolved.extend(f"{name}: {item}" for item in errors)
        special, special_errors = _exact_special(challenger, headroom=headroom)
        unresolved.extend(special_errors)
        total = None if structural is None or special is None else float(structural) + float(special)
        rows.append((challenger, structural, special, total, witness_sets))

    rows.sort(key=lambda item: (-(item[3] if item[3] is not None else -1e30), item[0].set_name.casefold()))
    winner = rows[0] if rows and rows[0][3] is not None else None
    runner_up = rows[1] if len(rows) > 1 and rows[1][3] is not None else None
    winner_name = None if winner is None else winner[0].set_name
    winner_total = None if winner is None else float(winner[3])
    runner_up_total = None if runner_up is None else float(runner_up[3])
    margin = None if winner_total is None or runner_up_total is None else winner_total - runner_up_total

    torc = next((item for item in rows if item[0].set_name == "Torc of Tonal Constancy"), None)
    torc_condition = None if torc is None else torc[0].condition
    torc_exact_flat = None if torc is None else torc[2]

    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        filtered.denominator_proven
        and ordinary.ordinary_denominator_proven
        and len(rows) == len(TARGETS)
        and all(item[3] is not None for item in rows)
        and winner_name == "Torc of Tonal Constancy"
        and winner_total is not None
        and winner_total > ORDINARY_INCUMBENT + 1e-9
        and margin is not None
        and margin > 1e-9
        and torc_exact_flat is not None
        and abs(float(torc_exact_flat) - 450.0) <= 1e-9
        and not unique_unresolved
    )

    print("EXTREME STAMINA RECOVERY SPECIAL NAMED-GEAR CHAMPION")
    print(f"database={database}")
    print(f"prior_ordinary_incumbent_prepercent={ORDINARY_INCUMBENT:.3f}")
    print(f"remaining_enlivening_headroom={headroom:.3f}")
    print()
    print("EXACT FINALISTS")
    for challenger, structural, special, total, witness_sets in rows:
        mm_exact = 0.0
        if challenger.max_magicka_kind is not None and challenger.max_magicka_value is not None:
            mm_exact = min(headroom, max(0.0, float(challenger.max_magicka_value)) * MAX_MAGICKA_TO_RECOVERY)
        print(
            f"set={challenger.set_name!r} pieces={challenger.piece_count} "
            f"structural={float(structural or 0.0):.3f} direct_special={float(challenger.flat or 0.0):.3f} "
            f"max_magicka_kind={challenger.max_magicka_kind!r} max_magicka_value={challenger.max_magicka_value!r} "
            f"exact_enlivening_from_special_max_magicka={mm_exact:.3f} "
            f"exact_special={float(special or 0.0):.3f} exact_total={float(total or 0.0):.3f} "
            f"condition={challenger.condition!r} witness_sets={witness_sets!r}"
        )
    print()
    print("CHAMPION")
    print(f"winner={winner_name!r}")
    print(f"winner_prepercent={float(winner_total or 0.0):.3f}")
    print(f"runner_up_prepercent={float(runner_up_total or 0.0):.3f}")
    print(f"winner_margin={float(margin or 0.0):.3f}")
    print(f"winner_beats_prior_ordinary_incumbent={bool(winner_total is not None and winner_total > ORDINARY_INCUMBENT + 1e-9)}")
    print(f"torc_condition={torc_condition!r}")
    print()
    print("PROOF GATES")
    print(f"medium_armor_physical_filter_proven={filtered.denominator_proven}")
    print(f"ordinary_denominator_prerequisite_proven={ordinary.ordinary_denominator_proven}")
    print(f"all_three_exactly_scored={len(rows) == len(TARGETS) and all(item[3] is not None for item in rows)}")
    print(f"torc_exact_450_branch={bool(torc_exact_flat is not None and abs(float(torc_exact_flat) - 450.0) <= 1e-9)}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"special_named_gear_champion_closed={closed}")
    print(
        "NEXT_STEP=promote Torc of Tonal Constancy as the named-gear incumbent and compose the Stamina Recovery contextual stack"
        if closed
        else "NEXT_STEP=close only the reported champion blockers"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
