from __future__ import annotations

"""Audit the reviewed legal class/subclass frontier for Extreme Weapon Damage.

This audit closes the class-passive/Class-Mastery comparison only. It deliberately
keeps concrete skill standing effects (for example, self-supplied named power
buffs) outside this slice because those depend on exact active-bar skill choices
and belong in the following joint skill/runtime proof.
"""

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.character_build.character_class import CharacterClass
from services.extreme_class_configuration_service import ExtremeClassConfigurationService
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService
from services.extreme_subclass_slot_allocation_service import ExtremeSubclassSlotAllocationService

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "weapon_damage"
DEFAULT_REFERENCES = (1000.0, 3000.0, 6000.0, 10000.0, 15000.0)


@dataclass(frozen=True)
class _Route:
    reference: float
    base_class: CharacterClass
    lines: tuple[str, ...]
    pure: bool
    projected_delta: float
    slot_counts: tuple[tuple[str, int], ...]
    sources: tuple[str, ...]
    runtime_conditions: tuple[str, ...]


def _best_subclass_route(reference: float) -> _Route | None:
    best: _Route | None = None
    for config in ExtremeClassConfigurationService.all_candidates():
        if config.is_pure_class:
            continue
        rows = ExtremeSubclassSlotAllocationService.reviewed_allocations(
            config.equipped_skill_lines,
            OBJECTIVE,
            reference_value=reference,
            include_known_zero=True,
        )
        if not rows:
            continue
        row = rows[0]
        candidate = _Route(
            reference=reference,
            base_class=config.base_class,
            lines=config.equipped_skill_lines,
            pure=False,
            projected_delta=float(row.projected_delta),
            slot_counts=row.slot_counts,
            sources=row.reviewed_sources,
            runtime_conditions=(),
        )
        if best is None or (
            candidate.projected_delta,
            tuple(source.casefold() for source in candidate.sources),
            candidate.base_class.value,
            candidate.lines,
        ) > (
            best.projected_delta,
            tuple(source.casefold() for source in best.sources),
            best.base_class.value,
            best.lines,
        ):
            best = candidate
    return best


def _best_pure_route(reference: float) -> _Route | None:
    service = ExtremeClassMasteryPairService(DATABASE)
    rows = service.best_pure_class_routes(
        OBJECTIVE,
        reference_value=reference,
    )
    if not rows:
        return None
    best = rows[0]
    config = next(
        row
        for row in ExtremeClassConfigurationService.candidates_for_base_class(best.base_class)
        if row.is_pure_class
    )
    return _Route(
        reference=reference,
        base_class=best.base_class,
        lines=config.equipped_skill_lines,
        pure=True,
        projected_delta=float(best.projected_delta or 0.0),
        slot_counts=(),
        sources=tuple(best.passive_names),
        runtime_conditions=tuple(best.conditions),
    )


def _best_route(reference: float) -> tuple[_Route | None, _Route | None, _Route | None]:
    pure = _best_pure_route(reference)
    subclass = _best_subclass_route(reference)
    rows = tuple(row for row in (pure, subclass) if row is not None)
    winner = max(
        rows,
        key=lambda row: (
            row.projected_delta,
            row.pure,
            row.base_class.value,
            row.lines,
        ),
        default=None,
    )
    return winner, pure, subclass


def main() -> int:
    print("EXTREME WEAPON DAMAGE CLASS ROUTE FRONTIER")
    print(f"database={DATABASE}")
    print(f"objective={OBJECTIVE}")
    print("scope=reviewed class passives plus legal pure-class Class Mastery selections")
    print("skill_standing_effects_in_scope=False")
    print()

    winners: list[_Route] = []
    unresolved: list[str] = []

    for reference in DEFAULT_REFERENCES:
        winner, pure, subclass = _best_route(reference)
        print(f"REFERENCE={reference:.3f}")
        if pure is None:
            unresolved.append(f"No reviewed pure-class route at reference {reference:g}")
            print("  pure=<none>")
        else:
            print(
                f"  pure class={pure.base_class.value} delta={pure.projected_delta:.3f} "
                f"mastery={pure.sources!r} conditions={pure.runtime_conditions!r}"
            )
        if subclass is None:
            unresolved.append(f"No reviewed subclass route at reference {reference:g}")
            print("  subclass=<none>")
        else:
            print(
                f"  subclass base={subclass.base_class.value} delta={subclass.projected_delta:.3f} "
                f"lines={subclass.lines!r} slots={subclass.slot_counts!r} sources={subclass.sources!r}"
            )
        if winner is not None:
            winners.append(winner)
            print(
                f"  winner={'pure' if winner.pure else 'subclass'} "
                f"class={winner.base_class.value} delta={winner.projected_delta:.3f}"
            )
        print()

    signatures = tuple(
        dict.fromkeys(
            (
                row.pure,
                row.base_class.value,
                row.lines,
                row.sources,
                row.runtime_conditions,
            )
            for row in winners
        )
    )
    reference_stable = bool(winners) and len(signatures) == 1

    print("FRONTIER SUMMARY")
    print(f"sample_count={len(DEFAULT_REFERENCES)}")
    print(f"distinct_winner_signatures={len(signatures)}")
    for signature in signatures:
        print(f"  winner_signature={signature!r}")
    print(f"reviewed_class_route_reference_stable={reference_stable}")
    print(f"unresolved_count={len(unresolved)}")
    for message in unresolved:
        print(f"  unresolved: {message}")

    closed = reference_stable and not unresolved
    print(f"reviewed_class_route_frontier_closed={closed}")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=jointly optimize the winning legal class route with exact active-bar "
        "standing skill effects and runtime power states, then compose that result with "
        "the exact named-gear winner for the final Weapon Damage snapshot"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
