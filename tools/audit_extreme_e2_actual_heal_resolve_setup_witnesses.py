from __future__ import annotations

"""Read-only audit of route-legal Resolve setup witnesses for Extreme H1.

This audit intentionally does not admit Seventh Legion Brute or mutate the ordinary-
gear denominator.  It asks the narrower prerequisite question: which canonical,
route-legal non-Ultimate active skills explicitly grant Major/Minor Resolve for each
Extreme class-line route?

Armor-domain matches are reported separately because route legality alone does not
prove worn-armor activation requirements.  Class/shared-combat matches are evidence
for the setup-action bridge; downstream gear admission still owns bar materialization
and candidate-heal displacement legality.
"""

from collections import Counter
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from services.extreme_actual_heal_setup_action_legality_service import (
    GRANTS_RESOLVE,
    ExtremeActualHealSetupActionLegalityService,
)
from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_player_skill_candidate_service import (
    ExtremePlayerSkillCandidateService,
    ExtremePlayerSkillLegalityContext,
)
from services.extreme_skill_universe_service import ExtremeSkillDomain


def main() -> int:
    database = get_data_dir() / "eso.db"
    candidate_service = ExtremePlayerSkillCandidateService(database)
    setup_service = ExtremeActualHealSetupActionLegalityService(
        candidate_service=candidate_service
    )
    route_service = ExtremeHealClassRouteService()
    routes = route_service.all_routes()

    route_rows: list[tuple[object, tuple[object, ...]]] = []
    skill_counts: Counter[tuple[str, str, str]] = Counter()
    domain_counts: Counter[str] = Counter()
    routes_with_any = 0
    routes_with_non_armor = 0
    routes_with_only_armor = 0
    routes_without_match = 0

    for route in routes:
        context = ExtremePlayerSkillLegalityContext(
            equipped_class_lines=route.equipped_skill_lines,
        )
        legal = candidate_service.candidates(context, ultimate=False)
        matches = tuple(
            row
            for row in legal
            if setup_service._supports(row, GRANTS_RESOLVE)  # audit exact bridge semantics
        )
        route_rows.append((route, matches))
        if matches:
            routes_with_any += 1
        else:
            routes_without_match += 1

        non_armor = tuple(row for row in matches if row.domain is not ExtremeSkillDomain.ARMOR)
        if non_armor:
            routes_with_non_armor += 1
        elif matches:
            routes_with_only_armor += 1

        for row in matches:
            skill_counts[(row.domain.value, row.skill_line, row.name)] += 1
            domain_counts[row.domain.value] += 1

    print("EXTREME E2 H1 RESOLVE SETUP-WITNESS AUDIT")
    print(f"database={database}")
    print(f"route_count={len(routes)}")
    print(f"routes_with_any_resolve_witness={routes_with_any}")
    print(f"routes_with_non_armor_resolve_witness={routes_with_non_armor}")
    print(f"routes_with_only_armor_resolve_witness={routes_with_only_armor}")
    print(f"routes_without_resolve_witness={routes_without_match}")
    print("DOMAIN MATCH COUNTS")
    for domain, count in sorted(domain_counts.items()):
        print(f"  {domain}: {count}")

    print("DISTINCT RESOLVE WITNESSES")
    for (domain, line, name), route_count in sorted(
        skill_counts.items(), key=lambda item: (item[0][0], item[0][1].casefold(), item[0][2].casefold())
    ):
        activation_note = (
            "worn-armor proof still required"
            if domain == ExtremeSkillDomain.ARMOR.value
            else "route-legal candidate evidence"
        )
        print(
            f"  domain={domain} line={line!r} skill={name!r} "
            f"routes={route_count} note={activation_note!r}"
        )

    print("ROUTES WITHOUT NON-ARMOR RESOLVE WITNESS")
    for route, matches in route_rows:
        non_armor = tuple(row for row in matches if row.domain is not ExtremeSkillDomain.ARMOR)
        if non_armor:
            continue
        armor_names = tuple(row.name for row in matches if row.domain is ExtremeSkillDomain.ARMOR)
        print(
            "  "
            f"base_class={route.base_class.value!r} "
            f"lines={route.equipped_skill_lines!r} "
            f"armor_only_matches={armor_names!r}"
        )

    print(
        "NEXT_STEP=do not admit Seventh Legion Brute globally unless the winning H1 candidate "
        "can materialize a legal Resolve-granting setup action without displacing the candidate "
        "heal; Armor witnesses additionally require worn-armor activation proof"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
