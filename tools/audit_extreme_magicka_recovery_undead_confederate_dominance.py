from __future__ import annotations

"""Prove Undead Confederate cannot win the Extreme Magicka Recovery class frontier.

The proof is deliberately split around the exact reference crossover.  Above the
crossover, the reviewed route beats the best runtime-obligation route at the same
class-independent Recovery reference even when Undead Confederate receives its full
conditional +155 ceiling.  Below the crossover, a small feasible reviewed package
(base Recovery + unboosted Atronach + three ordinary-strength Recovery glyphs)
produces an absolute total above the entire low-reference runtime upper bound.

This closes the class-route runtime obligation without claiming Spirit Mender uptime.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_MAGICKA_RECOVERY
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.mundus_repository import MundusRepository
from services.extreme_enchantment_objective_service import ExtremeEnchantmentObjectiveService
from services.extreme_mundus_objective_service import ExtremeMundusObjectiveService
from services.extreme_recovery_class_route_frontier_service import (
    ExtremeRecoveryClassRouteCandidate,
    ExtremeRecoveryClassRouteFrontierService,
)
from services.extreme_recovery_passive_special_branch_service import (
    ExtremeRecoveryPassiveBranchKind,
    ExtremeRecoveryPassiveSpecialBranchService,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService

OBJECTIVE = "magicka_recovery"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _candidate_key(row: ExtremeRecoveryClassRouteCandidate) -> tuple[object, ...]:
    return (
        row.base_class,
        row.equipped_skill_lines,
        row.slot_counts,
        row.runtime_obligations,
    )


def _best_runtime_candidate(result) -> ExtremeRecoveryClassRouteCandidate | None:
    rows = [row for row in result.candidates if row.runtime_obligations]
    return max(rows, key=lambda row: row.projected_delta, default=None)


def main() -> int:
    database = Path(_parser().parse_args().database)
    frontier = ExtremeRecoveryClassRouteFrontierService(database)

    at_zero = frontier.frontier(OBJECTIVE, reference_value=0.0)
    at_one = frontier.frontier(OBJECTIVE, reference_value=1.0)
    reviewed_zero = at_zero.best_reviewed_candidate
    reviewed_one = at_one.best_reviewed_candidate
    runtime_zero = _best_runtime_candidate(at_zero)
    runtime_one = _best_runtime_candidate(at_one)

    unresolved: list[str] = []
    if reviewed_zero is None or reviewed_one is None:
        unresolved.append("reviewed class frontier unavailable at reference 0/1")
    if runtime_zero is None or runtime_one is None:
        unresolved.append("runtime-obligation class route unavailable at reference 0/1")

    reviewed_intercept = float(reviewed_zero.projected_delta) if reviewed_zero else 0.0
    reviewed_slope = (
        float(reviewed_one.projected_delta) - reviewed_intercept if reviewed_one else 0.0
    )
    runtime_intercept = float(runtime_zero.projected_delta) if runtime_zero else 0.0
    runtime_slope = (
        float(runtime_one.projected_delta) - runtime_intercept if runtime_one else 0.0
    )

    if reviewed_zero and reviewed_one and _candidate_key(reviewed_zero) != _candidate_key(reviewed_one):
        unresolved.append("reviewed near-zero affine route identity changes between reference 0 and 1")
    if runtime_zero and runtime_one and _candidate_key(runtime_zero) != _candidate_key(runtime_one):
        unresolved.append("runtime near-zero affine route identity changes between reference 0 and 1")

    skills = ExtremeSkillUniverseService(database).all_player_skills()
    undead_rows = tuple(
        row for row in skills if row.is_passive and row.name.casefold() == "undead confederate"
    )
    undead_branch = None
    if len(undead_rows) == 1:
        undead_branch = ExtremeRecoveryPassiveSpecialBranchService.classify(
            undead_rows[0], OBJECTIVE
        )
    else:
        unresolved.append(f"expected one Undead Confederate passive, found {len(undead_rows)}")

    undead_ceiling = 0.0
    if (
        undead_branch is None
        or undead_branch.kind is not ExtremeRecoveryPassiveBranchKind.CONDITIONAL_FLAT
        or undead_branch.flat_ceiling is None
    ):
        unresolved.append("Undead Confederate conditional flat Recovery ceiling unresolved")
    else:
        undead_ceiling = float(undead_branch.flat_ceiling)

    slope_advantage = reviewed_slope - runtime_slope
    crossover_reference = float("inf")
    if slope_advantage <= 0.0:
        unresolved.append("reviewed near-zero route does not gain reference faster than runtime route")
    else:
        crossover_reference = (
            runtime_intercept + undead_ceiling - reviewed_intercept
        ) / slope_advantage
        if crossover_reference < 0.0:
            unresolved.append("computed Undead Confederate crossover reference is negative")

    mundus = ExtremeMundusObjectiveService.best_for_objective(
        MundusRepository(database, initialize=False),
        OBJECTIVE,
        multiplier=1.0,
    )
    jewelry = ExtremeEnchantmentObjectiveService.best_three_jewelry_loadout(
        JewelryGlyphEffectRepository(database),
        OBJECTIVE,
        slot_multipliers=(1.0, 1.0, 1.0),
    )

    if mundus is None or mundus.projected_delta is None or mundus.unresolved:
        unresolved.append("ordinary-strength Magicka Recovery Mundus witness unresolved")
        mundus_delta = 0.0
        mundus_name = "<unresolved>"
    else:
        mundus_delta = float(mundus.projected_delta)
        mundus_name = mundus.mundus_name

    if jewelry is None or jewelry.projected_delta is None or jewelry.unresolved:
        unresolved.append("ordinary-strength three-jewelry Recovery glyph witness unresolved")
        jewelry_delta = 0.0
        jewelry_name = "<unresolved>"
    else:
        jewelry_delta = float(jewelry.projected_delta)
        jewelry_name = jewelry.glyph_name

    feasible_reference = float(BASE_MAGICKA_RECOVERY) + mundus_delta + jewelry_delta
    feasible_result = frontier.frontier(OBJECTIVE, reference_value=feasible_reference)
    feasible_reviewed = feasible_result.best_reviewed_candidate
    feasible_runtime = _best_runtime_candidate(feasible_result)

    if feasible_reviewed is None:
        unresolved.append("reviewed route unavailable at feasible class-independent reference")
    if feasible_runtime is None:
        unresolved.append("runtime route unavailable at feasible class-independent reference")

    feasible_reviewed_total = (
        feasible_reference + float(feasible_reviewed.projected_delta)
        if feasible_reviewed is not None
        else 0.0
    )
    feasible_runtime_ceiling_total = (
        feasible_reference + float(feasible_runtime.projected_delta) + undead_ceiling
        if feasible_runtime is not None
        else 0.0
    )

    low_reference_runtime_upper_total = 0.0
    if crossover_reference != float("inf"):
        low_reference_runtime_upper_total = (
            crossover_reference
            + runtime_intercept
            + runtime_slope * crossover_reference
            + undead_ceiling
        )

    same_reference_dominated = (
        feasible_reviewed is not None
        and feasible_runtime is not None
        and feasible_reviewed_total > feasible_runtime_ceiling_total + 1e-9
    )
    low_reference_region_dominated = (
        feasible_reviewed is not None
        and feasible_reviewed_total > low_reference_runtime_upper_total + 1e-9
    )
    feasible_reference_above_crossover = feasible_reference > crossover_reference + 1e-9
    globally_dominated = all(
        (
            not unresolved,
            feasible_reference_above_crossover,
            same_reference_dominated,
            low_reference_region_dominated,
        )
    )

    print("EXTREME MAGICKA RECOVERY UNDEAD CONFEDERATE DOMINANCE")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print()
    print("NEAR-ZERO AFFINE ROUTES")
    if reviewed_zero is not None:
        print(f"reviewed_lines={reviewed_zero.equipped_skill_lines}")
    print(f"reviewed_formula={reviewed_intercept:.3f}+({reviewed_slope:.6f}*reference)")
    if runtime_zero is not None:
        print(f"runtime_lines={runtime_zero.equipped_skill_lines}")
        print(f"runtime_obligations={runtime_zero.runtime_obligations}")
    print(f"runtime_formula_before_condition={runtime_intercept:.3f}+({runtime_slope:.6f}*reference)")
    print(f"undead_confederate_flat_ceiling={undead_ceiling:.3f}")
    print(f"same_reference_crossover={crossover_reference:.3f}")
    print()
    print("CLASS-INDEPENDENT REVIEWED WITNESS")
    print(f"base_magicka_recovery={BASE_MAGICKA_RECOVERY:.3f}")
    print(f"mundus={mundus_name!r} ordinary_delta={mundus_delta:.3f}")
    print(f"jewelry_glyph={jewelry_name!r} three_slot_ordinary_delta={jewelry_delta:.3f}")
    print(f"feasible_common_reference={feasible_reference:.3f}")
    if feasible_reviewed is not None:
        print(f"feasible_reviewed_lines={feasible_reviewed.equipped_skill_lines}")
        print(f"feasible_reviewed_class_delta={feasible_reviewed.projected_delta:.3f}")
    if feasible_runtime is not None:
        print(f"feasible_runtime_lines={feasible_runtime.equipped_skill_lines}")
        print(f"feasible_runtime_class_delta_before_condition={feasible_runtime.projected_delta:.3f}")
    print(f"feasible_reviewed_total_before_shared_percent={feasible_reviewed_total:.3f}")
    print(f"feasible_runtime_total_with_full_undead_ceiling={feasible_runtime_ceiling_total:.3f}")
    print(f"same_reference_margin={feasible_reviewed_total - feasible_runtime_ceiling_total:.3f}")
    print()
    print("LOW-REFERENCE REGION")
    print(f"runtime_total_upper_bound_at_crossover={low_reference_runtime_upper_total:.3f}")
    print(f"reviewed_feasible_total={feasible_reviewed_total:.3f}")
    print(f"low_reference_margin={feasible_reviewed_total - low_reference_runtime_upper_total:.3f}")
    print()
    print("PROOF GATES")
    print(f"feasible_reference_above_crossover={feasible_reference_above_crossover}")
    print(f"same_reference_runtime_route_dominated={same_reference_dominated}")
    print(f"low_reference_runtime_region_dominated={low_reference_region_dominated}")
    print(f"unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")
    print(f"undead_confederate_globally_dominated={globally_dominated}")
    print(f"class_route_runtime_obligation_closed={globally_dominated}")
    if globally_dominated:
        print("NEXT_STEP=compose the piecewise reviewed class frontier with the whole-build Magicka Recovery reference")
        return 0
    print("NEXT_STEP=close the reported dominance proof gate before pruning Undead Confederate")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
