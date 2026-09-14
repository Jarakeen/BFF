from __future__ import annotations

"""Audit the legal four-slot Champion Point loadout for Extreme Magicka Recovery.

Static Recovery stars come from the canonical CP objective adapter. Dynamic or
conditional Recovery stars are bounded by the shared Recovery CP branch classifier.
The canonical ChampionPointLoadoutService then enforces four slots per discipline.
Runtime conditions remain explicit and are not treated as proven by slot legality.
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

    for record in repository.slottable_records():
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
    if not baseline.mechanic_complete:
        unresolved.extend(
            f"non-slottable {row.name}: {'; '.join(row.unresolved)}"
            for row in baseline.unresolved_candidates
        )

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
    print(f"mechanic_complete={baseline.mechanic_complete}")
    print()
    selected_enlivening = next(
        (row for row in loadout.selected if row.name.casefold() == "enlivening overflow"),
        None,
    )
    print("PROOF GATES")
    print(f"four_slot_loadout_denominator_proven={loadout.denominator_proven}")
    print(f"selected_enlivening_overflow={selected_enlivening is not None}")
    print(f"unresolved_count={len(tuple(dict.fromkeys(unresolved)))}")
    for item in tuple(dict.fromkeys(unresolved)):
        print(f"  unresolved: {item}")

    closed = loadout.denominator_proven and not unresolved
    print(f"magicka_recovery_cp_loadout_closed={closed}")
    if selected_enlivening is not None:
        print("NEXT_STEP=prove same-build Max Magicka reaches Enlivening Overflow's selected ceiling, then compose CP with the whole-build Recovery reference")
    elif closed:
        print("NEXT_STEP=compose the legal CP loadout with the whole-build Magicka Recovery reference")
    else:
        print("NEXT_STEP=close only the reported CP loadout blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
