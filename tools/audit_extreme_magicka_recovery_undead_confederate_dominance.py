from __future__ import annotations

"""Prove Undead Confederate cannot win the Extreme Magicka Recovery class frontier.

The proof avoids assuming one route owns the reviewed or runtime frontier near
reference zero. Instead it bounds every legal Living Death configuration using
its canonical static Recovery contribution plus the only reviewed active-bar
Recovery mechanics that can coexist with it: Flourish and Wellspring of the Abyss.

For references at or above one conservative common-build witness, the reviewed
Animal Companions + Curative Runeforms + Shadow route has at least as much slope
as every Living Death upper-bound branch and is already ahead at the witness.
For references below that witness, the runtime envelope is monotone, so its value
at the witness upper-bounds the entire lower region. The same feasible reviewed
build beats that upper bound. Undead Confederate receives its full conditional
+155 ceiling throughout; no Spirit Mender uptime assumption is needed.

The common witness intentionally uses only class-independent reviewed sources:
base Recovery, an unboosted Atronach, ordinary-strength Recovery jewelry glyphs,
and the strongest reviewed Magicka Recovery drink. It does not depend on race,
Divines, Infused, Champion Points, named gear, potion buffs, or Emperor state.
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
from minmax.passive_math import (
    ARCANIST_WELLSPRING_RECOVERY_PER_SLOTTED,
    WARDEN_FLOURISH_RECOVERY_PERCENT,
)
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
from services.extreme_recovery_provisioning_projection_service import (
    ExtremeRecoveryProvisioningProjectionService,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService
from services.extreme_subclass_slot_allocation_service import (
    ExtremeSubclassSlotAllocationService,
)

OBJECTIVE = "magicka_recovery"
LIVING_DEATH = "living_death"
ANIMAL_COMPANIONS = "animal_companions"
CURATIVE_RUNEFORMS = "curative_runeforms"
SHADOW = "shadow"
SOLDIER_OF_APOCRYPHA = "soldier_of_apocrypha"
REVIEWED_WITNESS_LINES = frozenset({ANIMAL_COMPANIONS, CURATIVE_RUNEFORMS, SHADOW})


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _find_reviewed_witness(
    candidates: tuple[ExtremeRecoveryClassRouteCandidate, ...],
) -> ExtremeRecoveryClassRouteCandidate | None:
    rows = [
        row
        for row in candidates
        if not row.runtime_obligations
        and frozenset(row.equipped_skill_lines) == REVIEWED_WITNESS_LINES
    ]
    return max(rows, key=lambda row: row.projected_delta, default=None)


def _living_death_rows(
    candidates: tuple[ExtremeRecoveryClassRouteCandidate, ...],
) -> tuple[ExtremeRecoveryClassRouteCandidate, ...]:
    return tuple(
        row
        for row in candidates
        if LIVING_DEATH in row.equipped_skill_lines
        and any("Undead Confederate" in item for item in row.runtime_obligations)
    )


def _runtime_slot_upper(
    lines: tuple[str, ...],
    reference: float,
) -> float:
    """Exact reviewed slot-mechanic upper bound for one Living Death line set."""

    line_set = set(lines)
    flourish = (
        float(reference) * float(WARDEN_FLOURISH_RECOVERY_PERCENT)
        if ANIMAL_COMPANIONS in line_set
        else 0.0
    )
    if SOLDIER_OF_APOCRYPHA not in line_set:
        return flourish

    per_slot = float(ARCANIST_WELLSPRING_RECOVERY_PER_SLOTTED)
    all_soldier = per_slot * float(ExtremeSubclassSlotAllocationService.ACTIVE_BAR_SLOTS)
    if ANIMAL_COMPANIONS not in line_set:
        return all_soldier

    # Flourish needs one Animal Companions ability represented. The remaining
    # five active-bar slots can then carry Soldier abilities for Wellspring.
    flourish_plus_soldier = flourish + per_slot * float(
        ExtremeSubclassSlotAllocationService.ACTIVE_BAR_SLOTS - 1
    )
    return max(all_soldier, flourish_plus_soldier)


def _runtime_upper_total(
    row: ExtremeRecoveryClassRouteCandidate,
    reference: float,
    undead_ceiling: float,
) -> float:
    static = float(row.static_flat) + float(row.static_percent) * float(reference)
    slot = _runtime_slot_upper(row.equipped_skill_lines, reference)
    return float(reference) + static + slot + float(undead_ceiling)


def _runtime_slope_upper(row: ExtremeRecoveryClassRouteCandidate) -> float:
    line_set = set(row.equipped_skill_lines)
    slot_slope = (
        float(WARDEN_FLOURISH_RECOVERY_PERCENT)
        if ANIMAL_COMPANIONS in line_set
        else 0.0
    )
    # Whole-build total contains the common reference itself.
    return 1.0 + float(row.static_percent) + slot_slope


def main() -> int:
    database = Path(_parser().parse_args().database)
    frontier = ExtremeRecoveryClassRouteFrontierService(database)
    unresolved: list[str] = []

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
    provisioning = ExtremeRecoveryProvisioningProjectionService.build(
        database,
        objective_key=OBJECTIVE,
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

    if (
        not provisioning.comparison_proven
        or provisioning.drink is None
        or provisioning.drink.delta <= 0.0
    ):
        unresolved.append("reviewed Magicka Recovery drink witness unresolved")
        provisioning_delta = 0.0
        provisioning_name = "<unresolved>"
    else:
        provisioning_delta = float(provisioning.drink.delta)
        provisioning_name = provisioning.drink.name

    feasible_reference = (
        float(BASE_MAGICKA_RECOVERY)
        + mundus_delta
        + jewelry_delta
        + provisioning_delta
    )
    feasible_result = frontier.frontier(OBJECTIVE, reference_value=feasible_reference)
    reviewed_witness = _find_reviewed_witness(feasible_result.candidates)
    runtime_rows = _living_death_rows(feasible_result.candidates)

    if reviewed_witness is None:
        unresolved.append("reviewed Animal Companions + Curative Runeforms + Shadow witness unavailable")
    if not runtime_rows:
        unresolved.append("no Living Death + Undead Confederate route candidates found")

    reviewed_total = (
        feasible_reference + float(reviewed_witness.projected_delta)
        if reviewed_witness is not None
        else 0.0
    )
    reviewed_slope = 0.0
    if reviewed_witness is not None:
        reviewed_slope = (
            1.0
            + float(reviewed_witness.static_percent)
            + float(WARDEN_FLOURISH_RECOVERY_PERCENT)
        )

    runtime_bounds = tuple(
        (
            row,
            _runtime_upper_total(row, feasible_reference, undead_ceiling),
            _runtime_slope_upper(row),
        )
        for row in runtime_rows
    )
    worst_runtime = max(runtime_bounds, key=lambda item: item[1], default=None)
    runtime_upper_at_witness = float(worst_runtime[1]) if worst_runtime else 0.0
    maximum_runtime_slope = max((item[2] for item in runtime_bounds), default=0.0)

    same_reference_margin = reviewed_total - runtime_upper_at_witness
    same_reference_dominated = reviewed_total > runtime_upper_at_witness + 1e-9
    high_reference_slope_dominated = reviewed_slope >= maximum_runtime_slope - 1e-12

    # Every component in the runtime upper bound is non-negative and non-decreasing
    # in the common reference. Therefore the value at feasible_reference bounds the
    # entire [0, feasible_reference] region. A fixed feasible reviewed build above
    # that ceiling globally dominates every lower-reference runtime build.
    low_reference_region_dominated = reviewed_total > runtime_upper_at_witness + 1e-9

    globally_dominated = all(
        (
            not unresolved,
            same_reference_dominated,
            high_reference_slope_dominated,
            low_reference_region_dominated,
        )
    )

    print("EXTREME MAGICKA RECOVERY UNDEAD CONFEDERATE DOMINANCE")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print()
    print("CLASS-INDEPENDENT REVIEWED WITNESS")
    print(f"base_magicka_recovery={BASE_MAGICKA_RECOVERY:.3f}")
    print(f"mundus={mundus_name!r} ordinary_delta={mundus_delta:.3f}")
    print(f"jewelry_glyph={jewelry_name!r} three_slot_ordinary_delta={jewelry_delta:.3f}")
    print(f"provisioning={provisioning_name!r} reviewed_delta={provisioning_delta:.3f}")
    print(f"feasible_common_reference={feasible_reference:.3f}")
    if reviewed_witness is not None:
        print(f"reviewed_lines={reviewed_witness.equipped_skill_lines}")
        print(f"reviewed_class_delta={reviewed_witness.projected_delta:.3f}")
        print(f"reviewed_whole_total={reviewed_total:.3f}")
        print(f"reviewed_whole_slope={reviewed_slope:.6f}")
    print()
    print("LIVING DEATH ENVELOPE")
    print(f"undead_confederate_flat_ceiling={undead_ceiling:.3f}")
    print(f"runtime_route_count={len(runtime_bounds)}")
    for row, upper, slope in sorted(
        runtime_bounds,
        key=lambda item: (-item[1], item[0].base_class, item[0].equipped_skill_lines),
    )[:8]:
        print(
            f"  upper_at_witness={upper:.3f} whole_slope_upper={slope:.6f} "
            f"base={row.base_class} lines={row.equipped_skill_lines}"
        )
    print(f"runtime_envelope_upper_at_witness={runtime_upper_at_witness:.3f}")
    print(f"maximum_runtime_whole_slope={maximum_runtime_slope:.6f}")
    print(f"same_reference_margin={same_reference_margin:.3f}")
    print()
    print("PROOF GATES")
    print(f"same_reference_runtime_envelope_dominated={same_reference_dominated}")
    print(f"high_reference_slope_dominated={high_reference_slope_dominated}")
    print(f"low_reference_monotone_envelope_dominated={low_reference_region_dominated}")
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
