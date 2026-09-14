from __future__ import annotations

"""Audit the legal four-slot Champion Point loadout for Extreme Magicka Recovery.

Static Recovery stars come from the canonical CP objective adapter. Dynamic or
conditional Recovery stars are bounded by the shared Recovery CP branch classifier.
The canonical ChampionPointLoadoutService then enforces four slots per discipline.
Runtime conditions remain explicit and are not treated as proven by slot legality.

Generic unresolved CP mechanics only block this audit when their own tooltip is
semantically capable of raising Magicka Recovery. Unrelated crafting, mitigation,
movement, loot, and other CP mechanics remain visible through the generic CP layer
but do not poison the Recovery objective denominator.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from services.champion_point_loadout_service import (
    CHAMPION_POINT_SLOTS_PER_DISCIPLINE,
    ChampionPointLoadoutCandidate,
    ChampionPointLoadoutService,
)
from services.extreme_champion_point_objective_service import ExtremeChampionPointObjectiveService
from services.extreme_recovery_champion_point_branch_service import (
    ExtremeRecoveryChampionPointBranchService,
)

OBJECTIVE = "magicka_recovery"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def main() -> int:
    database = Path(_parser().parse_args().database)
    repository = ChampionPointStaticRepository(database)
    unresolved: list[str] = []
    candidates: list[ChampionPointLoadoutCandidate] = []
    evidence: dict[str, str] = {}

    slottable_records = tuple(repository.slottable_records())
    non_slottable_records = tuple(repository.non_slottable_records())

    for record in slottable_records:
        projected = ExtremeChampionPointObjectiveService.candidate_for_record(
            repository,
            record,
            OBJECTIVE,
        )
        if projected.reviewed_delta is not None:
            delta = float(projected.reviewed_delta)
            if delta > 0.0:
                candidates.append(
                    ChampionPointLoadoutCandidate(
                        name=record.name,
                        discipline_index=record.discipline_index,
                        flat_ceiling=delta,
                        condition=None,
                    )
                )
                evidence[record.name.casefold()] = "canonical static CP projection"
            continue

        if not ExtremeRecoveryChampionPointBranchService.mentions_objective_recovery(
            record.description,
            OBJECTIVE,
        ):
            continue
        branch = ExtremeRecoveryChampionPointBranchService.classify(record, OBJECTIVE)
        if not branch.complete or branch.flat_ceiling is None:
            unresolved.extend(f"{record.name}: {item}" for item in branch.unresolved)
            continue
        candidates.append(
            ChampionPointLoadoutCandidate(
                name=record.name,
                discipline_index=record.discipline_index,
                flat_ceiling=float(branch.flat_ceiling),
                condition=branch.condition,
            )
        )
        evidence[record.name.casefold()] = f"shared Recovery CP branch: {branch.kind.value}"

    loadout = ChampionPointLoadoutService.build(tuple(candidates))
    unresolved.extend(loadout.unresolved)

    baseline = ExtremeChampionPointObjectiveService.non_slottable_baseline_for_objective(
        repository,
        OBJECTIVE,
    )
    non_slottable_by_name = {record.name.casefold(): record for record in non_slottable_records}
    relevant_non_slottable_unresolved: list[str] = []
    for row in baseline.unresolved_candidates:
        record = non_slottable_by_name.get(row.name.casefold())
        if record is None:
            relevant_non_slottable_unresolved.append(
                f"non-slottable {row.name}: canonical record identity unavailable"
            )
            continue
        if not ExtremeRecoveryChampionPointBranchService.mentions_objective_recovery(
            record.description,
            OBJECTIVE,
        ):
            continue
        relevant_non_slottable_unresolved.append(
            f"non-slottable {row.name}: {'; '.join(row.unresolved)}"
        )
    unresolved.extend(relevant_non_slottable_unresolved)

    print("EXTREME MAGICKA RECOVERY CHAMPION POINT LOADOUT")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print(f"slots_per_discipline={CHAMPION_POINT_SLOTS_PER_DISCIPLINE}")
    print()
    print("POSITIVE SLOTTABLE CANDIDATES")
    for row in sorted(
        candidates,
        key=lambda item: (
            item.discipline_index if item.discipline_index is not None else 10**9,
            -float(item.flat_ceiling),
            item.name.casefold(),
        ),
    ):
        print(
            f"  name={row.name!r} discipline={row.discipline_index} "
            f"ceiling={row.flat_ceiling:.3f} condition={row.condition or '<none>'} "
            f"evidence={evidence.get(row.name.casefold(), '<unknown>')}"
        )
    print()
    print("LEGAL LOADOUT")
    print(f"discipline_slot_counts={loadout.discipline_slot_counts}")
    print(f"selected_count={len(loadout.selected)}")
    for row in loadout.selected:
        print(
            f"  selected: {row.name} discipline={row.discipline_index} "
            f"ceiling={row.flat_ceiling:.3f} condition={row.condition or '<none>'}"
        )
    print(f"excluded_count={len(loadout.excluded)}")
    for row in loadout.excluded:
        print(
            f"  excluded: {row.name} discipline={row.discipline_index} "
            f"ceiling={row.flat_ceiling:.3f} condition={row.condition or '<none>'}"
        )
    print(f"slottable_total_flat_ceiling={loadout.total_flat_ceiling:.3f}")
    print()
    print("NON-SLOTTABLE BASELINE")
    print(f"reviewed_lower_bound={baseline.reviewed_lower_bound:.3f}")
    print(f"generic_mechanic_complete={baseline.mechanic_complete}")
    print(f"generic_unresolved_count={len(baseline.unresolved_candidates)}")
    print(f"recovery_relevant_unresolved_count={len(relevant_non_slottable_unresolved)}")
    print(f"recovery_relevant_mechanic_complete={not relevant_non_slottable_unresolved}")
    print()
    selected_enlivening = next(
        (row for row in loadout.selected if row.name.casefold() == "enlivening overflow"),
        None,
    )
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    print("PROOF GATES")
    print(f"four_slot_loadout_denominator_proven={loadout.denominator_proven}")
    print(f"selected_enlivening_overflow={selected_enlivening is not None}")
    print(f"non_slottable_recovery_denominator_proven={not relevant_non_slottable_unresolved}")
    print(f"unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")

    closed = (
        loadout.denominator_proven
        and not relevant_non_slottable_unresolved
        and not unique_unresolved
    )
    print(f"magicka_recovery_cp_loadout_closed={closed}")
    if selected_enlivening is not None and closed:
        print("NEXT_STEP=prove same-build Max Magicka reaches Enlivening Overflow's selected ceiling, then compose CP with the whole-build Recovery reference")
    elif selected_enlivening is not None:
        print("NEXT_STEP=close only the reported Recovery-relevant CP blockers, then prove Enlivening same-build Max Magicka")
    elif closed:
        print("NEXT_STEP=compose the legal CP loadout with the whole-build Magicka Recovery reference")
    else:
        print("NEXT_STEP=close only the reported CP loadout blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
