from __future__ import annotations

"""List exact unresolved condition markers in ordinary five-piece H1 gear rows.

Read-only. This audit is intentionally narrow: it extracts condition markers from
the same objective rows used by Extreme H1 so the remaining denominator debt can be
reviewed by exact condition family rather than coarse tooltip vocabulary.
"""

from collections import Counter, defaultdict
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from minmax.gear_set_repository import GearSetRepository
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


_CONDITION_RE = re.compile(r"requires condition (?P<condition>[^;]+)$", re.IGNORECASE)


def main() -> int:
    repository = GearSetRepository(Path(DEFAULT_DATABASE))
    repository.preload_all_static()

    grouped: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    non_condition: list[tuple[str, str, str]] = []

    for gear_set in repository.list_sets():
        useful = ExtremeGearSetObjectiveService._maximum_useful_piece_count(
            repository,
            gear_set,
        )
        if useful < 5:
            continue
        for objective in ExtremeActualHealGearSetCandidateService.OBJECTIVES:
            candidate = ExtremeGearSetObjectiveService.candidate_for_set(
                repository,
                gear_set.name,
                objective,
                equipped_piece_count=useful,
            )
            for message in candidate.unresolved:
                text = str(message)
                match = _CONDITION_RE.search(text)
                row = (str(gear_set.name), str(objective), text)
                if match:
                    grouped[match.group("condition").strip()].add(row)
                else:
                    non_condition.append(row)

    counts = Counter({condition: len(rows) for condition, rows in grouped.items()})

    print("EXTREME E2 ACTUAL HEAL ORDINARY GEAR CONDITION MARKERS")
    print(f"database={Path(DEFAULT_DATABASE)}")
    print(f"condition_marker_count={len(grouped)}")
    print(f"condition_blocker_row_count={sum(counts.values())}")
    print(f"non_condition_blocker_row_count={len(non_condition)}")
    print("BY CONDITION")
    for condition, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {condition}: rows={count}")
        for set_name, objective, message in sorted(
            grouped[condition],
            key=lambda row: (row[0].casefold(), row[1], row[2].casefold()),
        ):
            print(f"    {set_name}: objective={objective}")
            print(f"      {message}")

    print("NON-CONDITION BLOCKERS")
    for set_name, objective, message in sorted(
        non_condition,
        key=lambda row: (row[0].casefold(), row[1], row[2].casefold()),
    ):
        print(f"  {set_name}: objective={objective}")
        print(f"    {message}")

    print(
        "NEXT_STEP=close exact condition families only when H1 proves the condition "
        "irrelevant, scenario-owned, or explicitly constructible"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
