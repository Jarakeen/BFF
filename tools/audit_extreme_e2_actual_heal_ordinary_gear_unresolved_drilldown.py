from __future__ import annotations

"""Drill into unresolved ordinary five-piece H1 gear mechanics by objective/pattern.

Read-only. This audit does not change mechanic status and does not infer missing
set behavior. It exists to turn the remaining ordinary-set denominator debt into
reviewable families instead of one long list of set names.

Rows are gathered from the same canonical objective projection used by Extreme H1.
The audit reports objective counts, coarse description-pattern families, and a
bounded set of concrete unresolved examples for the largest families.
"""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
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


@dataclass(frozen=True)
class UnresolvedGearRow:
    set_name: str
    objective: str
    message: str
    pattern: str


def classify_unresolved_pattern(message: str) -> str:
    text = " ".join(str(message or "").casefold().split())
    if "weapon and spell damage" in text or "weapon or spell damage" in text:
        return "weapon_spell_damage"
    if "critical healing" in text or ("critical" in text and "healing" in text):
        return "critical_healing"
    if "healing" in text or re.search(r"\bheal(?:s|ed|ing)?\b", text):
        return "healing_or_heal_proc"
    if "maximum health" in text or "max health" in text:
        return "max_health"
    if "maximum magicka" in text or "max magicka" in text:
        return "max_magicka"
    if "maximum stamina" in text or "max stamina" in text:
        return "max_stamina"
    if "major courage" in text or "minor courage" in text:
        return "courage"
    if "major mending" in text or "minor mending" in text:
        return "mending"
    if "critical chance" in text:
        return "critical_chance"
    if "damage" in text:
        return "damage_other"
    if "resource" in text or "magicka" in text or "stamina" in text:
        return "resource_other"
    if "not yet mechanic-mapped" in text:
        return "opaque_or_other_unmapped"
    return "other_blocker"


def build_unresolved_rows(repository: GearSetRepository) -> tuple[UnresolvedGearRow, ...]:
    repository.preload_all_static()
    rows: list[UnresolvedGearRow] = []
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
                rows.append(
                    UnresolvedGearRow(
                        set_name=str(gear_set.name),
                        objective=str(objective),
                        message=str(message),
                        pattern=classify_unresolved_pattern(message),
                    )
                )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row.objective,
                row.pattern,
                row.set_name.casefold(),
                row.message.casefold(),
            ),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples-per-family", type=int, default=8)
    args = parser.parse_args()

    rows = build_unresolved_rows(GearSetRepository(Path(args.database)))
    by_objective = Counter(row.objective for row in rows)
    by_family = Counter((row.objective, row.pattern) for row in rows)
    sets_by_objective: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        sets_by_objective[row.objective].add(row.set_name)

    print("EXTREME E2 ACTUAL HEAL ORDINARY GEAR UNRESOLVED DRILLDOWN")
    print(f"database={Path(args.database)}")
    print(f"unresolved_message_count={len(rows)}")
    print(f"unresolved_set_count={len({row.set_name for row in rows})}")
    print("BY OBJECTIVE")
    for objective in ExtremeActualHealGearSetCandidateService.OBJECTIVES:
        print(
            f"  {objective}: messages={by_objective[objective]} "
            f"sets={len(sets_by_objective[objective])}"
        )

    print("BY OBJECTIVE + PATTERN")
    grouped: dict[tuple[str, str], list[UnresolvedGearRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.objective, row.pattern)].append(row)

    limit = max(1, int(args.examples_per_family))
    for key, count in sorted(by_family.items(), key=lambda item: (-item[1], item[0])):
        objective, pattern = key
        family_rows = grouped[key]
        family_sets = {row.set_name for row in family_rows}
        print(
            f"  {objective} / {pattern}: messages={count} sets={len(family_sets)}"
        )
        seen_examples: set[tuple[str, str]] = set()
        emitted = 0
        for row in family_rows:
            identity = (row.set_name, row.message)
            if identity in seen_examples:
                continue
            seen_examples.add(identity)
            print(f"    {row.set_name}: {row.message}")
            emitted += 1
            if emitted >= limit:
                break

    print(
        "NEXT_STEP=review the largest objective/pattern families and add only proof-safe "
        "screening or explicit mechanic mappings; opaque descriptions remain unresolved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
