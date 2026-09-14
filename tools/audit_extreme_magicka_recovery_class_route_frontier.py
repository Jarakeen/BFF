from __future__ import annotations

"""Inspect the reviewed Extreme Magicka Recovery class/subclass route frontier.

The reference grid is diagnostic only. Recovery routes can mix flat and percentage
contributions, so a winner that changes with the pre-class Recovery subtotal is a
frontier result, not a closed global record. Contextual runtime obligations remain
explicit until separately witnessed.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_recovery_class_route_frontier_service import (
    ExtremeRecoveryClassRouteFrontierService,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument(
        "--references",
        type=float,
        nargs="+",
        default=(1000.0, 2500.0, 5000.0, 10000.0),
        help="Diagnostic pre-class Recovery reference values.",
    )
    parser.add_argument("--top", type=int, default=8)
    return parser


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    service = ExtremeRecoveryClassRouteFrontierService(database)

    print("EXTREME MAGICKA RECOVERY CLASS ROUTE FRONTIER")
    print(f"database={database}")
    print("mode=diagnostic_reference_grid_not_final_record")

    winners: list[tuple[float, tuple[str, ...], str, float]] = []
    union_obligations: set[str] = set()

    for reference in args.references:
        result = service.frontier("magicka_recovery", reference_value=float(reference))
        union_obligations.update(result.unresolved_runtime_obligations)
        best = result.best_reviewed_candidate
        print()
        print(f"REFERENCE={reference:.3f}")
        if best is None:
            print("  best=<none>")
            continue
        winners.append(
            (
                float(reference),
                best.equipped_skill_lines,
                best.base_class,
                best.projected_delta,
            )
        )
        print(
            f"  best base_class={best.base_class} pure={best.is_pure_class} "
            f"lines={best.equipped_skill_lines} projected_delta={best.projected_delta:.3f}"
        )
        print(
            f"  components static_flat={best.static_flat:.3f} "
            f"static_percent={best.static_percent:.3%} "
            f"slot_delta={best.slot_projected_delta:.3f} "
            f"mastery_delta={best.mastery_projected_delta:.3f}"
        )
        print(f"  slot_counts={best.slot_counts}")
        for source in best.reviewed_sources:
            print(f"    source: {source}")
        if best.runtime_obligations:
            for obligation in best.runtime_obligations:
                print(f"    runtime: {obligation}")

        print("  top reviewed routes:")
        for index, row in enumerate(result.candidates[: max(1, args.top)], start=1):
            print(
                f"    {index:02d}. delta={row.projected_delta:.3f} "
                f"base={row.base_class} pure={row.is_pure_class} "
                f"lines={row.equipped_skill_lines} slots={row.slot_counts}"
            )

    distinct_winner_lines = tuple(dict.fromkeys(row[1] for row in winners))
    print()
    print("FRONTIER SUMMARY")
    print(f"distinct_reviewed_winner_line_sets={len(distinct_winner_lines)}")
    for lines in distinct_winner_lines:
        print(f"  winner_lines={lines}")
    print(f"runtime_obligation_count={len(union_obligations)}")
    for obligation in sorted(union_obligations, key=str.casefold):
        print(f"  runtime_obligation={obligation}")

    reference_stable = len(distinct_winner_lines) <= 1 and bool(winners)
    print(f"reviewed_winner_reference_stable={reference_stable}")
    print("class_route_record_closed=False")
    if union_obligations:
        print("NEXT_STEP=close runtime obligations on competitive Magicka Recovery class routes before route dominance proof")
    elif not reference_stable:
        print("NEXT_STEP=derive crossover bounds and compose the class frontier with the whole-build Recovery subtotal")
    else:
        print("NEXT_STEP=compose the stable reviewed class route with the whole-build Magicka Recovery frontier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
