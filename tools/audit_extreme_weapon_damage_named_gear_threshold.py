from __future__ import annotations

"""Audit legal named-gear Weapon Damage against the Sword-and-Board threshold.

The weapon-passive audit reduced the topology contest to Dual Wield versus the
One Hand and Shield Sword-and-Board +3% sheet-power modifier.  At zero common
percentage modifiers, Sword-and-Board needs at least 14113.333 non-weapon
pre-percent Weapon Damage to overtake the corrected Dual Wield witness.  Positive
common percentage modifiers only increase that required baseline.

This audit does not invent a whole-build number.  It exhaustively reuses the
canonical named-set breakpoint/topology/slot-legality pipeline, finds the largest
reviewed legal named-gear Weapon Damage package, and reports how much threshold
headroom remains for race/class/CP/jewelry/Mundus/runtime flats.  Any unresolved
named-set mechanic remains explicit and keeps the named-gear denominator open.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "weapon_damage"
SWORD_BOARD_THRESHOLD = 14113.333


def main() -> int:
    repository = GearSetRepository(DATABASE)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(DATABASE).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
        OBJECTIVE,
        breakpoints,
    )
    realization = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    ).build(topology)

    evidence_by_pair = {
        (int(row.set_id), int(row.piece_count)): row
        for row in relevance.evidence
    }

    best_score = float("-inf")
    best_signature: tuple[tuple[str, int], ...] = ()
    realized_count = 0
    missing_evidence: list[str] = []

    for topology_row in realization.realization.topologies:
        for witness in topology_row.realizations:
            realized_count += 1
            score = 0.0
            signature: list[tuple[str, int]] = []
            for set_id, set_name, count in zip(
                witness.set_ids,
                witness.set_names,
                witness.counts,
                strict=True,
            ):
                evidence = evidence_by_pair.get((int(set_id), int(count)))
                if evidence is None:
                    missing_evidence.append(
                        f"Missing Weapon Damage relevance evidence for {set_name!r} at {count} pieces"
                    )
                    continue
                signature.append((str(set_name), int(count)))
                # reviewed_delta is safe for exact ordinary resolved breakpoints.
                # Relevant-but-unresolved mechanics are kept separately below and
                # are never silently scored as zero proof.
                score += max(0.0, float(evidence.reviewed_delta))
            candidate_signature = tuple(signature)
            if (
                score > best_score + 1e-9
                or (
                    abs(score - best_score) <= 1e-9
                    and candidate_signature < best_signature
                )
            ):
                best_score = score
                best_signature = candidate_signature

    if best_score == float("-inf"):
        best_score = 0.0

    unresolved_evidence = tuple(
        row
        for row in relevance.evidence
        if row.status is ExtremeGearSetObjectiveRelevance.UNRESOLVED
    )
    unresolved = tuple(
        dict.fromkeys(
            (
                *relevance.unresolved,
                *realization.unresolved,
                *missing_evidence,
            )
        )
    )

    headroom = SWORD_BOARD_THRESHOLD - best_score

    print("EXTREME WEAPON DAMAGE NAMED-GEAR / SWORD-BOARD THRESHOLD AUDIT")
    print(f"database={DATABASE}")
    print(f"objective={OBJECTIVE}")
    print()
    print("NAMED GEAR DENOMINATOR")
    print(f"breakpoints_reviewed={len(relevance.evidence)}")
    print(f"relevant_breakpoints={len(relevance.relevant)}")
    print(f"unresolved_breakpoints={len(unresolved_evidence)}")
    print(f"assignments_considered={realization.assignments_considered}")
    print(f"assignments_realized={realization.assignments_realized}")
    print(f"assignments_rejected={realization.assignments_rejected}")
    print(f"realization_truncated={realization.truncated}")
    print(f"realization_denominator_proven={realization.denominator_proven}")
    print()
    print("BEST REVIEWED LEGAL NAMED-GEAR PACKAGE")
    print(f"best_named_gear_reviewed_flat_delta={best_score:.3f}")
    print(f"best_named_gear_signature={best_signature!r}")
    print()
    print("SWORD AND BOARD THRESHOLD")
    print(f"sword_board_minimum_preweapon_flat_baseline={SWORD_BOARD_THRESHOLD:.3f}")
    print(f"threshold_headroom_after_named_gear_only={headroom:.3f}")
    print("threshold_uses_common_percent_zero=True")
    print("positive_common_percent_only_raises_threshold=True")
    print()
    print("PROOF GATES")
    print(f"named_gear_relevance_denominator_proven={relevance.denominator_proven}")
    print(f"named_gear_realization_denominator_proven={realization.denominator_proven}")
    print(f"unresolved_count={len(unresolved)}")
    for row in unresolved:
        print(f"  unresolved: {row}")
    closed = relevance.denominator_proven and realization.denominator_proven and not unresolved
    print(f"weapon_damage_named_gear_denominator_closed={closed}")
    print(
        "NEXT_STEP=add the already-closed nonweapon flat maxima (base, race, jewelry, Mundus, CP, Courage, enchant proc, class/runtime flats) to the best legal named-gear package; if that conservative total remains below the Sword-and-Board threshold, Dual Wield is the proven weapon champion"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
