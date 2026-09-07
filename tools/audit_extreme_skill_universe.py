from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.extreme_passive_projection_service import (
    ExtremePassiveProjectionService,
)
from services.extreme_skill_universe_service import (
    ExtremeSkillDomain,
    ExtremeSkillUniverseService,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit every canonical player skill/passive available to Extreme Builds. "
            "Inventory is complete-by-DB-row; numeric mechanic coverage may remain partial."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--show-unresolved",
        action="store_true",
        help="Print every unresolved/context-required passive after the summary.",
    )
    args = parser.parse_args()

    universe = ExtremeSkillUniverseService(args.database)
    skills = universe.all_player_skills()
    passives = tuple(row for row in skills if row.is_passive)
    actives = tuple(row for row in skills if not row.is_passive)
    projections = ExtremePassiveProjectionService.project_all(passives)

    skill_by_domain = Counter(row.domain.value for row in skills)
    active_by_domain = Counter(row.domain.value for row in actives)
    passive_by_domain = Counter(row.domain.value for row in passives)
    status_by_domain: dict[str, Counter[str]] = defaultdict(Counter)
    for projection in projections:
        status_by_domain[projection.passive.domain.value][projection.status.value] += 1

    print("EXTREME PLAYER SKILL UNIVERSE AUDIT")
    print(f"Database:   {args.database}")
    print("Mode:       READ ONLY")
    print("Boundary:   every canonical player skill is inventoried; unresolved mechanics are not guessed")
    print()
    print(f"Player skills: {len(skills)}")
    print(f"Actives:       {len(actives)}")
    print(f"Passives:      {len(passives)}")

    for domain in ExtremeSkillDomain:
        key = domain.value
        total = skill_by_domain[key]
        if not total:
            continue
        statuses = status_by_domain[key]
        print()
        print(f"{key}")
        print(f"  skills:   {total}")
        print(f"  actives:  {active_by_domain[key]}")
        print(f"  passives: {passive_by_domain[key]}")
        for status in (
            "reviewed_static",
            "context_required",
            "known_noncombat",
            "unresolved",
        ):
            if statuses[status]:
                print(f"  {status}: {statuses[status]}")

    status_totals = Counter(projection.status.value for projection in projections)
    print()
    print("PASSIVE PROJECTION SUMMARY")
    for status in (
        "reviewed_static",
        "context_required",
        "known_noncombat",
        "unresolved",
    ):
        print(f"{status:18} {status_totals[status]}")

    accounted = sum(status_totals.values())
    print()
    print(f"Passives accounted for: {accounted}/{len(passives)}")
    print(f"Missing from classification: {len(passives) - accounted}")

    if args.show_unresolved:
        print()
        print("CONTEXT / UNRESOLVED PASSIVES")
        for projection in projections:
            if projection.status.value not in {"context_required", "unresolved"}:
                continue
            passive = projection.passive
            print(
                f"- [{passive.domain.value}] {passive.skill_line} :: {passive.name} "
                f"=> {projection.status.value}"
            )
            for condition in projection.conditions:
                print(f"    condition: {condition}")
            for message in projection.unresolved:
                print(f"    {message}")

    print()
    print("BOUNDARY")
    print("Inventory coverage is not mechanic coverage. A passive is never assigned zero value merely because its mechanic is unresolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
