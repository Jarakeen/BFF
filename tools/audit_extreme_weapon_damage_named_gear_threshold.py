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
* one identity may be reused across different piece counts, and physical slot
  conflicts are ignored, but repeated positions at the same count use distinct
  set identities.

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
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_gear_set_power_upper_bound_service import (
    ExtremeGearSetPowerUpperBoundService,
)

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "weapon_damage"
SWORD_BOARD_THRESHOLD = 14113.333


def _bounded_flat_for_evidence(row) -> tuple[float, tuple[str, ...]]:
    """Return a safe flat ceiling for one breakpoint or explicit blockers."""

    target_stats = ExtremeGearSetObjectiveService._target_stats(OBJECTIVE)
    flat = 0.0
    blockers: list[str] = []

    for effect in row.candidate.source_effects:
        if effect.stat not in target_stats or float(effect.value) <= 0.0:
            continue
        operation = effect.operation
        if operation is EffectOperation.ADD:
            # Conditional/scoped target effects are deliberately assumed active
            # in this ceiling even when exact execution remains unresolved.
            flat += float(effect.value)
        elif operation is EffectOperation.ADD_PERCENT:
            blockers.append(
                f"{row.set_name} {row.piece_count}pc: positive percentage Weapon Damage set effect requires separate stacking bound ({float(effect.value):g})"
            )
        else:
            blockers.append(
                f"{row.set_name} {row.piece_count}pc: unsupported positive Weapon Damage operation in upper-bound audit: {operation}"
            )

    resolver = GearSetEffectResolver()
    for bonus in row.candidate.source_bonuses:
        if resolver.resolve(bonus, use_max_value=True, source=row.set_name):
            continue
        bound = ExtremeGearSetPowerUpperBoundService.build(
            str(bonus.description or ""),
            OBJECTIVE,
        )
        flat += float(bound.flat_upper_bound)
        if bound.percent_upper_bound > 0.0:
            blockers.append(
                f"{row.set_name} {row.piece_count}pc: positive percentage Weapon Damage "
                f"set effect requires separate stacking bound ({bound.percent_upper_bound:g})"
            )
        blockers.extend(
            f"{row.set_name} {row.piece_count}pc: {message}"
            for message in bound.unresolved
        )

    if row.status is ExtremeGearSetObjectiveRelevance.UNRESOLVED and not blockers and flat <= 0.0:
        blockers.append(f"{row.set_name} {row.piece_count}pc: unresolved power bonus has no finite upper bound")

    return float(flat), tuple(blockers)


def _relaxed_distinct_topology_bound(
    by_count: dict[int, list[tuple[float, str, int]]],
    topologies,
) -> tuple[float, tuple[tuple[str, int], ...]]:
    """Return the strongest relaxed topology with distinct identities per count."""

    best_score = 0.0
    best_signature: tuple[tuple[str, int], ...] = ()
    for topology_row in topologies:
        score = 0.0
        parts: list[tuple[str, int]] = []
        counts = tuple(int(value) for value in topology_row.counts)
        for count in sorted(set(counts)):
            needed = counts.count(count)
            candidates = by_count.get(count, ())
            # One named set identity cannot occupy two separate positions of the
            # same topology. We still allow the same identity to appear at two
            # different piece counts and ignore physical slot conflicts, so this
            # remains an intentionally favorable upper bound.
            ordered = sorted(
                candidates,
                key=lambda item: (-item[0], item[1].casefold(), item[2]),
            )
            chosen: list[tuple[float, str, int]] = []
            seen_set_ids: set[int] = set()
            for candidate in ordered:
                set_id = int(candidate[2])
                if set_id in seen_set_ids:
                    continue
                seen_set_ids.add(set_id)
                chosen.append(candidate)
                if len(chosen) == needed:
                    break
            score += sum(max(0.0, float(value)) for value, _name, _set_id in chosen)
            parts.extend((name, count) for _value, name, _set_id in chosen)
            # A topology position may be occupied by an objective-irrelevant
            # set. Zero is therefore a safe contribution for unfilled positions.
            parts.extend(
                ("<zero objective contribution>", count)
                for _ in range(needed - len(chosen))
            )
        signature = tuple(parts)
        if score > best_score + 1e-9 or (
            abs(score - best_score) <= 1e-9
            and (not best_signature or signature < best_signature)
        ):
            best_score = score
            best_signature = signature
    return float(best_score), best_signature


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

    best_score, best_signature = _relaxed_distinct_topology_bound(
        by_count,
        topology.topologies,
    )

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
    print("same_count_duplicate_set_identities_allowed_in_bound=False")
    print("cross_count_duplicate_set_identities_allowed_in_bound=True")
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
