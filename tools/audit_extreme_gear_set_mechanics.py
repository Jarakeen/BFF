from __future__ import annotations

"""Audit canonical gear-set mechanic coverage for Extreme Builds.

This tool is intentionally read-only. It inventories every canonical set bonus
row and asks the shared GearSetEffectResolver whether the mechanic is currently
understood. Inventory coverage is not mechanic coverage: an unresolved bonus is
reported explicitly and is never interpreted as zero contribution.
"""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_repository import GearSetRepository


STATIC = "reviewed_static"
CONDITIONAL = "reviewed_conditional"
UNRESOLVED = "unresolved"
EMPTY = "empty_description"


def classify_bonus(resolver: GearSetEffectResolver, bonus, *, set_name: str) -> tuple[str, tuple[str, ...]]:
    description = str(bonus.description or "").strip()
    if not description:
        return EMPTY, ()

    source = f"{set_name} ({bonus.piece_count})"
    effects = tuple(
        resolver.resolve(
            bonus,
            use_max_value=True,
            source=source,
        )
    )
    if not effects:
        return UNRESOLVED, ()
    if any(effect.condition for effect in effects):
        conditions = tuple(
            sorted(
                {
                    str(effect.condition)
                    for effect in effects
                    if effect.condition
                }
            )
        )
        return CONDITIONAL, conditions
    return STATIC, ()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit canonical gear-set mechanic coverage for Extreme Builds."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="ESO SQLite database path (default: canonical data/eso.db)",
    )
    parser.add_argument(
        "--show-unresolved",
        action="store_true",
        help="Print every unresolved/empty set bonus after the summary.",
    )
    args = parser.parse_args()

    database = Path(args.database)
    if not database.is_file():
        raise FileNotFoundError(f"ESO database not found: {database}")

    repository = GearSetRepository(database)
    resolver = GearSetEffectResolver()

    totals: Counter[str] = Counter()
    category_totals: dict[str, Counter[str]] = defaultdict(Counter)
    piece_totals: dict[int, Counter[str]] = defaultdict(Counter)
    unresolved_rows: list[tuple[str, str, int, str, str]] = []

    sets = tuple(repository.list_sets())
    bonus_count = 0

    for gear_set in sets:
        category = str(gear_set.category or "uncategorized")
        for bonus in repository.get_bonuses(gear_set.id):
            bonus_count += 1
            classification, conditions = classify_bonus(
                resolver,
                bonus,
                set_name=gear_set.name,
            )
            totals[classification] += 1
            category_totals[category][classification] += 1
            piece_totals[int(bonus.piece_count)][classification] += 1

            if classification in {UNRESOLVED, EMPTY}:
                unresolved_rows.append(
                    (
                        gear_set.name,
                        category,
                        int(bonus.piece_count),
                        classification,
                        str(bonus.description or "").strip(),
                    )
                )

    resolved = totals[STATIC] + totals[CONDITIONAL]

    print("EXTREME GEAR-SET MECHANIC COVERAGE AUDIT")
    print("Mode:       READ ONLY")
    print(f"Database:   {database}")
    print(
        "Boundary:   inventory coverage is not mechanic coverage; unresolved bonuses are blockers, not zero"
    )
    print()

    print("SUMMARY")
    print(f"Canonical sets:                     {len(sets)}")
    print(f"Canonical bonus rows:               {bonus_count}")
    print(f"Reviewed static bonus rows:         {totals[STATIC]}")
    print(f"Reviewed conditional bonus rows:    {totals[CONDITIONAL]}")
    print(f"Unresolved bonus rows:              {totals[UNRESOLVED]}")
    print(f"Empty-description bonus rows:       {totals[EMPTY]}")
    print(f"Mechanically recognized rows:       {resolved}")
    coverage = (resolved / bonus_count * 100.0) if bonus_count else 0.0
    print(f"Recognized-row coverage:            {coverage:.2f}%")
    print()

    print("BY CATEGORY")
    for category in sorted(category_totals, key=str.casefold):
        counts = category_totals[category]
        total = sum(counts.values())
        print(
            f"{category}: total={total} static={counts[STATIC]} "
            f"conditional={counts[CONDITIONAL]} unresolved={counts[UNRESOLVED]} "
            f"empty={counts[EMPTY]}"
        )
    print()

    print("BY PIECE THRESHOLD")
    for piece_count in sorted(piece_totals):
        counts = piece_totals[piece_count]
        total = sum(counts.values())
        print(
            f"{piece_count} piece(s): total={total} static={counts[STATIC]} "
            f"conditional={counts[CONDITIONAL]} unresolved={counts[UNRESOLVED]} "
            f"empty={counts[EMPTY]}"
        )

    if args.show_unresolved:
        print()
        print("UNRESOLVED / EMPTY BONUS ROWS")
        for set_name, category, piece_count, classification, description in sorted(
            unresolved_rows,
            key=lambda row: (row[0].casefold(), row[2], row[3]),
        ):
            print(
                f"- {set_name} | {category} | {piece_count} piece(s) | {classification}"
            )
            print(f"  {description or '<empty description>'}")

    print()
    print("BOUNDARY")
    print(
        "A resolved 2/3/4-piece stat line may contribute to an Extreme reviewed lower bound even when a later active set bonus remains unresolved. The unresolved mechanic still blocks a complete/global claim."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
