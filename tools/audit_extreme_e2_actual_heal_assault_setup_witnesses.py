from __future__ import annotations

"""Read-only route audit for H1 Assault setup witnesses used by Powerful Assault."""

from collections import Counter
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from services.extreme_actual_heal_setup_action_legality_service import (
    IS_ASSAULT_ABILITY,
    ExtremeActualHealSetupActionLegalityService,
)
from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext


def main() -> int:
    database = get_data_dir() / "eso.db"
    setup = ExtremeActualHealSetupActionLegalityService(database)
    routes = ExtremeHealClassRouteService().all_routes()

    proven = 0
    missing: list[object] = []
    witnesses: Counter[tuple[str, str]] = Counter()
    evidence: dict[tuple[str, str], str] = {}

    for route in routes:
        context = ExtremePlayerSkillLegalityContext(
            equipped_class_lines=route.equipped_skill_lines,
        )
        witness = setup.witness(IS_ASSAULT_ABILITY, context)
        if not witness.proven:
            missing.append(route)
            continue
        proven += 1
        key = (str(witness.skill_line or ""), str(witness.skill_name or ""))
        witnesses[key] += 1
        evidence[key] = str(witness.evidence or "")

    print("EXTREME E2 H1 ASSAULT SETUP-WITNESS AUDIT")
    print(f"database={database}")
    print(f"route_count={len(routes)}")
    print(f"routes_with_assault_witness={proven}")
    print(f"routes_without_assault_witness={len(missing)}")
    print("DISTINCT ASSAULT WITNESSES")
    for (line, name), count in sorted(
        witnesses.items(),
        key=lambda item: (item[0][0].casefold(), item[0][1].casefold()),
    ):
        print(
            f"  line={line!r} skill={name!r} routes={count} "
            f"evidence={evidence[(line, name)]!r}"
        )

    if missing:
        print("ROUTES WITHOUT ASSAULT WITNESS")
        for route in missing[:50]:
            print(
                f"  base_class={route.base_class.value!r} "
                f"lines={route.equipped_skill_lines!r}"
            )
        if len(missing) > 50:
            print(f"  ... {len(missing) - 50} additional routes")

    print(
        "NEXT_STEP=admit Powerful Assault only if every relevant H1 route has a route-legal "
        "non-Ultimate Assault witness that can be materialized on the inactive bar"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
