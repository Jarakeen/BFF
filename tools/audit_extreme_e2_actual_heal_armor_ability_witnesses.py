from __future__ import annotations

"""Read-only audit for Armor Master active-bar Armor ability witnesses."""

from collections import Counter
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from minmax.gear_set_repository import GearSetRepository
from services.extreme_actual_heal_setup_action_legality_service import (
    IS_ARMOR_ABILITY,
    ExtremeActualHealSetupActionLegalityService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext


ARMOR_LINES = ("Light Armor", "Medium Armor", "Heavy Armor")


def main() -> int:
    database = get_data_dir() / "eso.db"
    setup = ExtremeActualHealSetupActionLegalityService(database)
    repository = GearSetRepository(database)
    objective_row = ExtremeGearSetObjectiveService.candidate_for_set(
        repository,
        "Armor Master",
        "max_health",
    )
    proven = 0
    witnesses: Counter[tuple[str, str]] = Counter()
    missing: list[str] = []
    for line in ARMOR_LINES:
        witness = setup.witness(
            IS_ARMOR_ABILITY,
            ExtremePlayerSkillLegalityContext(
                equipped_class_lines=(),
                equipped_armor_lines=(line,),
            ),
        )
        if witness.proven:
            proven += 1
            witnesses[(str(witness.skill_line or ""), str(witness.skill_name or ""))] += 1
        else:
            missing.append(line)

    print("EXTREME E2 H1 ARMOR-MASTER ACTIVE-BAR WITNESS AUDIT")
    print(f"database={database}")
    print(f"armor_line_count={len(ARMOR_LINES)}")
    print(f"armor_lines_with_witness={proven}")
    print(f"armor_lines_without_witness={len(missing)}")
    print("DISTINCT ARMOR-ABILITY WITNESSES")
    for (line, name), count in sorted(witnesses.items()):
        print(f"  line={line!r} skill={name!r} armor_lines={count}")

    print("CANONICAL ARMOR MASTER MAX-HEALTH OBJECTIVE")
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
        unit = getattr(getattr(effect, "unit", None), "value", getattr(effect, "unit", None))
        print(
            f"  effect stat={stat!r} operation={operation!r} unit={unit!r} "
            f"value={effect.value!r} condition={effect.condition!r} source={effect.source!r}"
        )
    print(f"  unresolved_count={len(objective_row.unresolved)}")
    for blocker in objective_row.unresolved:
        print(f"  unresolved={blocker!r}")

    if missing:
        print("ARMOR LINES WITHOUT WITNESS")
        for line in missing:
            print(f"  line={line!r}")
    print(
        "NEXT_STEP=admit Armor Master only when a compatible Armor active remains "
        "materialized on the scored active bar"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
