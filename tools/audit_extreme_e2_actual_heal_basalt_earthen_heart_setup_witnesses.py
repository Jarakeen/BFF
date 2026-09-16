from __future__ import annotations

"""Read-only route audit for Basalt-Blooded Warrior Earthen Heart setup witnesses."""

from collections import Counter
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from minmax.gear_set_repository import GearSetRepository
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_setup_action_legality_service import (
    IS_EARTHEN_HEART_ABILITY,
    ExtremeActualHealSetupActionLegalityService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext


def _line_id(value: object) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value or "").strip().casefold().replace("'", ""),
    ).strip("_")


def main() -> int:
    database = get_data_dir() / "eso.db"
    setup = ExtremeActualHealSetupActionLegalityService(database)
    routes = ExtremeHealClassRouteService().all_routes()
    repository = GearSetRepository(database)
    objective_row = ExtremeGearSetObjectiveService.candidate_for_set(
        repository,
        "Basalt-Blooded Warrior",
        "healing_done",
    )
    h1_review = ExtremeActualHealGearConditionRelevanceService.review(objective_row)

    relevant = 0
    proven = 0
    false_positive: list[object] = []
    false_negative: list[object] = []
    witnesses: Counter[tuple[str, str]] = Counter()

    for route in routes:
        owns_earthen_heart = any(
            _line_id(line) == "earthen_heart"
            for line in route.equipped_skill_lines
        )
        context = ExtremePlayerSkillLegalityContext(
            equipped_class_lines=route.equipped_skill_lines,
        )
        witness = setup.witness(IS_EARTHEN_HEART_ABILITY, context)
        if owns_earthen_heart:
            relevant += 1
            if witness.proven:
                proven += 1
                witnesses[(str(witness.skill_line or ""), str(witness.skill_name or ""))] += 1
            else:
                false_negative.append(route)
        elif witness.proven:
            false_positive.append(route)

    print("EXTREME E2 H1 BASALT EARTHEN-HEART SETUP-WITNESS AUDIT")
    print(f"database={database}")
    print(f"route_count={len(routes)}")
    print(f"earthen_heart_route_count={relevant}")
    print(f"earthen_heart_routes_with_witness={proven}")
    print(f"false_positive_routes={len(false_positive)}")
    print(f"false_negative_routes={len(false_negative)}")
    print("DISTINCT EARTHEN-HEART WITNESSES")
    for (line, name), count in sorted(witnesses.items()):
        print(f"  line={line!r} skill={name!r} routes={count}")

    print("CANONICAL BASALT HEALING OBJECTIVE")
    print(f"  reviewed_delta={objective_row.reviewed_delta!r}")
    print(f"  source_effect_count={len(objective_row.source_effects)}")
    for bonus in objective_row.source_bonuses:
        if int(bonus.piece_count) == 5:
            print(f"  five_piece_description={str(bonus.description or '')!r}")
    for effect in objective_row.source_effects:
        stat = getattr(getattr(effect, "stat", None), "value", getattr(effect, "stat", None))
        operation = getattr(
            getattr(effect, "operation", None),
            "value",
            getattr(effect, "operation", None),
        )
        print(
            f"  effect stat={stat!r} operation={operation!r} value={effect.value!r} "
            f"condition={effect.condition!r} source={effect.source!r}"
        )
    print(f"  unresolved_count={len(objective_row.unresolved)}")
    for blocker in objective_row.unresolved:
        print(f"  unresolved={blocker!r}")
    print(f"  h1_mechanic_complete={h1_review.h1_mechanic_complete}")
    print(f"  h1_positive_modifier_proven={h1_review.h1_positive_modifier_proven}")
    for blocker in h1_review.remaining_blockers:
        print(f"  h1_remaining_blocker={blocker!r}")

    for label, rows in (
        ("FALSE POSITIVE ROUTES", false_positive),
        ("FALSE NEGATIVE ROUTES", false_negative),
    ):
        if rows:
            print(label)
            for route in rows[:50]:
                print(
                    f"  base_class={route.base_class.value!r} "
                    f"lines={route.equipped_skill_lines!r}"
                )

    print(
        "NEXT_STEP=admit Basalt-Blooded Warrior only for explicit Earthen Heart routes "
        "with a materializable primary/front-bar setup and a secondary/back-bar scored heal"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
