from __future__ import annotations

"""Prove Wrathsun cannot borrow the unconstrained Magicka Recovery class route.

Wrathsun's 5pc requires damaging with a Dawn's Wrath ability. Therefore any legal
Wrathsun scoring state must both equip the Dawn's Wrath class line and reserve at
least one active-bar slot for a Dawn's Wrath skill. This audit reuses the canonical
Recovery class-route frontier and reviewed six-slot allocator, then recomputes the
best class contribution under those two constraints.

The default Recovery reference and Willow score are the exact outputs from the
preceding physical Wrathsun/Willow audits. They remain CLI arguments so a future
data refresh can rerun the proof without editing this file.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_recovery_class_route_frontier_service import (
    ExtremeRecoveryClassRouteFrontierService,
    _line_id,
)
from services.extreme_subclass_slot_allocation_service import (
    ExtremeSubclassSlotAllocationService,
)

OBJECTIVE = "magicka_recovery"
REQUIRED_LINE = "dawns_wrath"
ARMOR_RECOVERY_PERCENT = 0.28


@dataclass(frozen=True)
class ForcedRouteResult:
    base_class: str
    equipped_skill_lines: tuple[str, ...]
    slot_counts: tuple[tuple[str, int], ...]
    class_delta: float
    final_score: float
    runtime_obligations: tuple[str, ...]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument(
        "--reference",
        type=float,
        default=5153.884,
        help="Wrathsun pre-armor/pre-class Recovery subtotal from the preceding gear audit.",
    )
    parser.add_argument(
        "--willow-final",
        type=float,
        default=9259.238,
        help="Constructive Willow final score from the preceding Willow audit.",
    )
    return parser


def forced_wrathsun_routes(
    service: ExtremeRecoveryClassRouteFrontierService,
    *,
    reference_value: float,
) -> tuple[ForcedRouteResult, ...]:
    frontier = service.frontier(OBJECTIVE, reference_value=reference_value)
    rows: list[ForcedRouteResult] = []

    for candidate in frontier.candidates:
        line_ids = {_line_id(line) for line in candidate.equipped_skill_lines}
        if REQUIRED_LINE not in line_ids:
            continue

        allocations = ExtremeSubclassSlotAllocationService.reviewed_allocations(
            candidate.equipped_skill_lines,
            OBJECTIVE,
            reference_value=reference_value,
            include_known_zero=True,
        )
        legal_allocations = tuple(
            allocation
            for allocation in allocations
            if dict(allocation.slot_counts).get(REQUIRED_LINE, 0) >= 1
        )
        if not legal_allocations:
            continue

        allocation = legal_allocations[0]
        non_slot_delta = float(candidate.projected_delta) - float(candidate.slot_projected_delta)
        class_delta = non_slot_delta + float(allocation.projected_delta)
        final_score = float(reference_value) * (1.0 + ARMOR_RECOVERY_PERCENT) + class_delta
        rows.append(
            ForcedRouteResult(
                base_class=candidate.base_class,
                equipped_skill_lines=candidate.equipped_skill_lines,
                slot_counts=allocation.slot_counts,
                class_delta=class_delta,
                final_score=final_score,
                runtime_obligations=candidate.runtime_obligations,
            )
        )

    return tuple(
        sorted(
            rows,
            key=lambda row: (
                -row.final_score,
                row.base_class,
                row.equipped_skill_lines,
                row.slot_counts,
            ),
        )
    )


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    reference = float(args.reference)
    willow_final = float(args.willow_final)
    service = ExtremeRecoveryClassRouteFrontierService(database)

    unconstrained = service.frontier(OBJECTIVE, reference_value=reference)
    unconstrained_best = unconstrained.best_reviewed_candidate
    forced = forced_wrathsun_routes(service, reference_value=reference)
    best = forced[0] if forced else None

    unresolved: list[str] = []
    if unconstrained_best is None:
        unresolved.append("no unconstrained reviewed class-route candidate")
    if best is None:
        unresolved.append("no legal Dawn's Wrath route with at least one active-bar slot")
    if best is not None:
        unresolved.extend(best.runtime_obligations)

    forced_final = best.final_score if best is not None else 0.0
    margin_to_willow = willow_final - forced_final
    dominated = best is not None and margin_to_willow > 1e-9
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(best is not None and not unique_unresolved and dominated)

    print("EXTREME MAGICKA RECOVERY WRATHSUN CLASS-ROUTE CONSTRAINT")
    print(f"database={database}")
    print(f"wrathsun_preclass_reference={reference:.3f}")
    print(f"willow_constructive_final={willow_final:.3f}")
    if unconstrained_best is not None:
        unconstrained_final = reference * (1.0 + ARMOR_RECOVERY_PERCENT) + float(
            unconstrained_best.projected_delta
        )
        print(f"unconstrained_class_delta={unconstrained_best.projected_delta:.3f}")
        print(f"unconstrained_final={unconstrained_final:.3f}")
        print(f"unconstrained_lines={unconstrained_best.equipped_skill_lines!r}")
        print(f"unconstrained_slots={unconstrained_best.slot_counts!r}")
    if best is not None:
        print(f"forced_dawns_wrath_class_delta={best.class_delta:.3f}")
        print(f"forced_dawns_wrath_final={best.final_score:.3f}")
        print(f"forced_lines={best.equipped_skill_lines!r}")
        print(f"forced_slots={best.slot_counts!r}")
        print(f"forced_base_class={best.base_class}")
    print(f"margin_to_willow={margin_to_willow:.3f}")
    print(f"dominated={dominated}")
    print()
    print("PROOF GATES")
    print(f"dawns_wrath_line_required=True")
    print(f"dawns_wrath_active_slot_required=True")
    print(f"forced_route_found={best is not None}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"wrathsun_branch_closed={closed}")
    print(
        "NEXT_STEP=remove Wrathsun from the Willow-rebased flat survivor queue"
        if closed
        else "NEXT_STEP=close only the reported Wrathsun class-route blockers"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
