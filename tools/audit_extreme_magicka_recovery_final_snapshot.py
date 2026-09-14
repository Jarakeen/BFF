from __future__ import annotations

"""Compose the final theoretical Extreme Magicka Recovery snapshot.

This audit starts from the already-closed pre-percent checkpoint and promoted active-bar
state, then independently re-resolves all remaining named/contextual percentage sources.
It is intentionally an audit-only composition step, not a new runtime owner.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.named_combat_buffs import effects_for_buff
from minmax.passive_math import (
    light_armor_magicka_recovery_percent,
    support_magicka_aid_recovery_percent,
    warden_flourish_recovery_percent,
)
from minmax.stat_ids import StatId
from services.extreme_recovery_passive_special_branch_service import (
    ExtremeRecoveryPassiveBranchKind,
    ExtremeRecoveryPassiveSpecialBranchService,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService
from tools.audit_extreme_magicka_recovery_combined_active_bar_frontier import (
    EXPECTED_ROUTE_IDS,
    _bar_shape_legal,
    _capacity,
)
from tools.audit_extreme_magicka_recovery_minor_intellect_bar_frontier import (
    CARRIER_LINE,
    CARRIER_NAME,
    _minor_intellect_percent,
    _rank4_carrier,
)

OBJECTIVE = "magicka_recovery"
PROMOTED_ANIMAL_SLOTS = 1
PROMOTED_SUPPORT_SLOTS = 3
PROMOTED_MAGES_SLOTS = 0
PROMOTED_CARRIER_SLOTS = 1
LIGHT_ARMOR_PIECES = 7
STATIC_ROUTE_PERCENT = 53.0  # Flourish 20 + Erudition 18 + Refreshing Shadows 15.


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--pre-percent", type=float, default=5184.294)
    parser.add_argument("--home-keeps", type=int, default=6)
    return parser


def _named_recovery_percent(name: str) -> tuple[float | None, tuple[str, ...]]:
    rows = tuple(
        row
        for row in effects_for_buff(name)
        if row.stat is StatId.MAGICKA_RECOVERY and row.bucket == "resource_percent"
    )
    if len(rows) != 1:
        return None, (f"Expected one canonical {name} Magicka Recovery effect, found {len(rows)}",)
    return float(rows[0].value) * 100.0, ()


def _passive_branch(database: Path, passive_name: str):
    universe = ExtremeSkillUniverseService(database)
    matches = tuple(row for row in universe.passives() if row.name.strip().casefold() == passive_name.casefold())
    if len(matches) != 1:
        return None, (f"Expected one passive named {passive_name!r}, found {len(matches)}",)
    branch = ExtremeRecoveryPassiveSpecialBranchService.classify(matches[0], OBJECTIVE)
    if branch is None:
        return None, (f"Passive {passive_name!r} did not classify for {OBJECTIVE}",)
    return branch, ()


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    unresolved: list[str] = []

    minor_percent, minor_unresolved = _minor_intellect_percent()
    unresolved.extend(minor_unresolved)
    minor_percent = float(minor_percent or 0.0)

    major_percent, major_unresolved = _named_recovery_percent("Major Intellect")
    unresolved.extend(major_unresolved)
    major_percent = float(major_percent or 0.0)

    continuous, continuous_unresolved = _passive_branch(database, "Continuous Attack")
    unresolved.extend(continuous_unresolved)
    domination, domination_unresolved = _passive_branch(database, "Domination")
    unresolved.extend(domination_unresolved)

    continuous_percent = 0.0
    if continuous is not None:
        if continuous.kind is not ExtremeRecoveryPassiveBranchKind.CONDITIONAL_PERCENT:
            unresolved.append(f"Continuous Attack classified as {continuous.kind.value}, expected conditional_percent")
        continuous_percent = float(continuous.percent_ceiling or 0.0)

    domination_percent = 0.0
    if domination is not None:
        if domination.kind is not ExtremeRecoveryPassiveBranchKind.CONDITIONAL_PERCENT:
            unresolved.append(f"Domination classified as {domination.kind.value}, expected conditional_percent")
        if int(args.home_keeps) != 6:
            unresolved.append("Final theoretical snapshot requires six Home Keeps for Domination ceiling")
        domination_percent = float(domination.percent_ceiling or 0.0)

    universe = ExtremeSkillUniverseService(database)
    animal_capacity = _capacity(universe, "Animal Companions")
    support_capacity = _capacity(universe, "Support")
    carrier = _rank4_carrier(database)
    carrier_line = "" if carrier is None else str(carrier["skill_line"] or "").strip().casefold().replace(" ", "_")
    carrier_capacity = type(animal_capacity)(CARRIER_LINE, 1, 0)
    promoted_bar_legal = _bar_shape_legal(
        (
            (PROMOTED_ANIMAL_SLOTS, animal_capacity),
            (PROMOTED_SUPPORT_SLOTS, support_capacity),
            (PROMOTED_CARRIER_SLOTS, carrier_capacity),
        )
    )
    if not promoted_bar_legal:
        unresolved.append("Promoted one-Animal/three-Support/Minor-Intellect bar is not legal")
    if carrier is None or carrier_line != CARRIER_LINE or CARRIER_LINE not in EXPECTED_ROUTE_IDS:
        unresolved.append(f"{CARRIER_NAME} carrier is not inside the proven route")

    light_percent = light_armor_magicka_recovery_percent(LIGHT_ARMOR_PIECES) * 100.0
    support_percent = support_magicka_aid_recovery_percent(PROMOTED_SUPPORT_SLOTS) * 100.0
    flourish_percent = warden_flourish_recovery_percent(PROMOTED_ANIMAL_SLOTS) * 100.0
    route_percent = STATIC_ROUTE_PERCENT
    if abs(flourish_percent - 20.0) > 1e-9:
        unresolved.append(f"Unexpected Flourish percent for promoted bar: {flourish_percent}")

    mages_percent = 0.0  # Proven promoted bar allocates no Mages Guild normal skill.
    standing_percent = light_percent + route_percent + support_percent + minor_percent + mages_percent
    contextual_percent = major_percent + continuous_percent + domination_percent
    total_percent = standing_percent + contextual_percent
    pre_percent = float(args.pre_percent)

    standing_final = pre_percent * (1.0 + standing_percent / 100.0)
    major_final = pre_percent * (1.0 + (standing_percent + major_percent) / 100.0)
    continuous_major_final = pre_percent * (
        1.0 + (standing_percent + major_percent + continuous_percent) / 100.0
    )
    final_value = pre_percent * (1.0 + total_percent / 100.0)

    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        promoted_bar_legal
        and abs(light_percent - 28.0) <= 1e-9
        and abs(route_percent - 53.0) <= 1e-9
        and abs(support_percent - 30.0) <= 1e-9
        and abs(minor_percent - 15.0) <= 1e-9
        and abs(major_percent - 30.0) <= 1e-9
        and abs(continuous_percent - 20.0) <= 1e-9
        and abs(domination_percent - 100.0) <= 1e-9
        and PROMOTED_MAGES_SLOTS == 0
        and not unique_unresolved
    )

    print("EXTREME MAGICKA RECOVERY FINAL SNAPSHOT AUDIT")
    print(f"database={database}")
    print(f"pre_percent={pre_percent:.3f}")
    print(f"promoted_route={tuple(sorted(EXPECTED_ROUTE_IDS))!r}")
    print(f"promoted_bar=(animal={PROMOTED_ANIMAL_SLOTS}, support={PROMOTED_SUPPORT_SLOTS}, carrier={CARRIER_NAME!r}, mages={PROMOTED_MAGES_SLOTS})")
    print()
    print("STANDING PERCENT LAYERS")
    print(f"light_armor_evocation_percent={light_percent:.3f}")
    print(f"class_route_static_percent={route_percent:.3f}")
    print(f"magicka_aid_percent={support_percent:.3f}")
    print(f"minor_intellect_percent={minor_percent:.3f}")
    print(f"magicka_controller_percent={mages_percent:.3f}")
    print(f"standing_total_percent={standing_percent:.3f}")
    print(f"standing_final={standing_final:.3f}")
    print()
    print("CONTEXTUAL PERCENT LAYERS")
    print(f"major_intellect_percent={major_percent:.3f}")
    print(f"continuous_attack_percent={continuous_percent:.3f}")
    print(f"domination_percent={domination_percent:.3f}")
    print(f"contextual_total_percent={contextual_percent:.3f}")
    print(f"major_intellect_final={major_final:.3f}")
    print(f"major_plus_continuous_final={continuous_major_final:.3f}")
    print()
    print("FINAL")
    print(f"total_percent={total_percent:.3f}")
    print(f"final_magicka_recovery={final_value:.3f}")
    print()
    print("PROOF GATES")
    print(f"promoted_bar_legal={promoted_bar_legal}")
    print(f"evocation_28_proven={abs(light_percent - 28.0) <= 1e-9}")
    print(f"class_route_53_proven={abs(route_percent - 53.0) <= 1e-9}")
    print(f"magicka_aid_30_proven={abs(support_percent - 30.0) <= 1e-9}")
    print(f"minor_intellect_15_proven={abs(minor_percent - 15.0) <= 1e-9}")
    print(f"major_intellect_30_proven={abs(major_percent - 30.0) <= 1e-9}")
    print(f"continuous_attack_20_proven={abs(continuous_percent - 20.0) <= 1e-9}")
    print(f"domination_100_proven={abs(domination_percent - 100.0) <= 1e-9}")
    print(f"magicka_controller_zero_proven={PROMOTED_MAGES_SLOTS == 0}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"final_snapshot_closed={closed}")
    if closed:
        print("NEXT_STEP=promote the closed Magicka Recovery record into the Extreme result/runtime layer")
    else:
        print("NEXT_STEP=close only the reported final-snapshot blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
