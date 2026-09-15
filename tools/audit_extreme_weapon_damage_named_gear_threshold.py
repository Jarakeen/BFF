from __future__ import annotations

"""Fast proof-safe named-gear upper bound for Extreme Weapon Damage.

The earlier audit exhaustively realized every named-set assignment. That is more
work than this particular proof needs and can be prohibitively slow. Sword and
Board only needs a conservative upper bound on non-weapon pre-percent Weapon
Damage. This audit therefore reuses the canonical breakpoint, topology, and
objective-relevance catalogs but deliberately over-credits named gear:

* every positive conditional flat is assumed active;
* for each set-count position in a legal topology, the strongest canonical
  Weapon Damage breakpoint at that count is used;
* duplicate set identities and slot conflicts are allowed in the bound.

Those relaxations can only make the named-gear number larger. Positive
percentage Weapon Damage set effects are not flattened; they remain explicit
proof blockers because they could change the Sword-and-Board comparison.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "weapon_damage"
SWORD_BOARD_THRESHOLD = 14113.333


def _bounded_flat_for_evidence(row) -> tuple[float, tuple[str, ...]]:
    """Return a safe flat ceiling for one breakpoint or explicit blockers."""

    target_stats = ExtremeGearSetObjectiveService._target_stats(OBJECTIVE)
    flat = max(0.0, float(row.reviewed_delta))
    blockers: list[str] = []
    saw_target = False

    for effect in row.candidate.source_effects:
        if effect.stat not in target_stats or float(effect.value) <= 0.0:
            continue
        saw_target = True
        operation = effect.operation
        if operation is EffectOperation.ADD:
            flat = max(flat, float(effect.value))
        elif operation is EffectOperation.ADD_PERCENT:
            blockers.append(
                f"{row.set_name} {row.piece_count}pc: positive percentage Weapon Damage set effect requires separate stacking bound ({float(effect.value):g})"
            )
        else:
            blockers.append(
                f"{row.set_name} {row.piece_count}pc: unsupported positive Weapon Damage operation in upper-bound audit: {operation}"
            )

    if (
        row.status is ExtremeGearSetObjectiveRelevance.UNRESOLVED
        and not saw_target
        and flat <= 0.0
    ):
        blockers.append(
            f"{row.set_name} {row.piece_count}pc: unresolved Weapon Damage breakpoint has no bounded target-stat effect"
        )

    return float(flat), tuple(blockers)


def _named_gear_upper_bound():
    repository = GearSetRepository(DATABASE)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
        OBJECTIVE,
        breakpoints,
    )

    by_count: dict[int, list[tuple[float, str, int]]] = {}
    blockers: list[str] = [*breakpoints.unresolved, *topology.unresolved]
    bounded_unresolved = 0

    for row in relevance.evidence:
        if row.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
            continue
        flat, row_blockers = _bounded_flat_for_evidence(row)
        blockers.extend(row_blockers)
        if row.status is ExtremeGearSetObjectiveRelevance.UNRESOLVED and not row_blockers:
            bounded_unresolved += 1
        by_count.setdefault(int(row.piece_count), []).append(
            (float(flat), str(row.set_name), int(row.set_id))
        )

    best_score = 0.0
    best_signature: tuple[tuple[str, int], ...] = ()
    for topology_row in topology.topologies:
        score = 0.0
        parts: list[tuple[str, int]] = []
        for count in tuple(int(value) for value in topology_row.counts):
            candidates = by_count.get(count, ())
            if not candidates:
                # A topology position may be occupied by an objective-irrelevant
                # set. Zero is therefore a safe contribution for this position.
                parts.append(("<zero objective contribution>", count))
                continue
            value, name, _set_id = max(
                candidates,
                key=lambda item: (item[0], item[1].casefold(), item[2]),
            )
            score += max(0.0, float(value))
            parts.append((name, count))
        signature = tuple(parts)
        if score > best_score + 1e-9 or (
            abs(score - best_score) <= 1e-9
            and (not best_signature or signature < best_signature)
        ):
            best_score = score
            best_signature = signature

    blockers = list(dict.fromkeys(message for message in blockers if message))
    proven = bool(topology.topologies) and not blockers
    return (
        float(best_score),
        best_signature,
        proven,
        tuple(blockers),
        relevance,
        topology,
        bounded_unresolved,
    )


def main() -> int:
    (
        best_score,
        best_signature,
        bound_proven,
        blockers,
        relevance,
        topology,
        bounded_unresolved,
    ) = _named_gear_upper_bound()

    headroom = SWORD_BOARD_THRESHOLD - best_score

    print("EXTREME WEAPON DAMAGE FAST NAMED-GEAR UPPER BOUND")
    print(f"database={DATABASE}")
    print(f"objective={OBJECTIVE}")
    print()
    print("CANONICAL DENOMINATOR INPUT")
    print(f"breakpoints_reviewed={len(relevance.evidence)}")
    print(f"relevant_breakpoints={len(relevance.relevant)}")
    print(f"raw_unresolved_breakpoints={len(relevance.unresolved_evidence)}")
    print(f"bounded_unresolved_breakpoints={bounded_unresolved}")
    print(f"topology_count={len(topology.topologies)}")
    print(f"max_topology_parts={max((len(row.counts) for row in topology.topologies), default=0)}")
    print()
    print("CONSERVATIVE NAMED-GEAR BOUND")
    print(f"named_gear_flat_upper_bound={best_score:.3f}")
    print(f"upper_bound_signature={best_signature!r}")
    print("duplicate_set_identities_allowed_in_bound=True")
    print("slot_conflicts_ignored_in_bound=True")
    print("conditional_flats_assumed_active=True")
    print()
    print("SWORD AND BOARD THRESHOLD")
    print(f"sword_board_minimum_preweapon_flat_baseline={SWORD_BOARD_THRESHOLD:.3f}")
    print(f"threshold_headroom_after_named_gear_upper_bound={headroom:.3f}")
    print("threshold_uses_common_percent_zero=True")
    print("positive_common_percent_only_raises_threshold=True")
    print()
    print("PROOF GATES")
    print(f"named_gear_upper_bound_proven={bound_proven}")
    print(f"unbound_named_gear_mechanic_count={len(blockers)}")
    for message in blockers:
        print(f"  unresolved: {message}")
    print(f"weapon_damage_named_gear_threshold_bound_closed={bound_proven}")
    print(
        "NEXT_STEP=use this fast conservative named-gear ceiling in the whole-build preweapon upper-bound audit; exact named-set realization is unnecessary for the Sword-and-Board dominance proof"
    )
    return 0 if bound_proven else 2


if __name__ == "__main__":
    raise SystemExit(main())
