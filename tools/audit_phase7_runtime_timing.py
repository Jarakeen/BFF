from __future__ import annotations

"""Audit canonical Phase 7 cadence extraction over the real boundary corpus."""

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_runtime_timing import extract_skill_component_runtime_timing
from tools.audit_phase7_runtime_boundaries import load_phase7_runtime_boundaries

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Phase 7 boundary rows against canonical runtime timing extraction."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--samples", type=int, default=80)
    args = parser.parse_args()

    rows = load_phase7_runtime_boundaries(args.database)
    resolved = []
    unresolved = []
    kinds: Counter[str] = Counter()

    for row in rows:
        timing = extract_skill_component_runtime_timing(row.fragment)
        if timing is None:
            unresolved.append(row)
            continue
        resolved.append((row, timing))
        kinds[timing.bound_kind.value] += 1

    print("\n========================================")
    print(" PHASE 7 RUNTIME TIMING AUDIT")
    print("========================================")
    print(f"Database:                 {args.database}")
    print(f"Phase 7 boundary rows:    {len(rows)}")
    print(f"Timing resolved:          {len(resolved)}")
    print(f"Timing unresolved:        {len(unresolved)}")

    print("\nBOUND KINDS")
    if kinds:
        for name, count in kinds.most_common():
            print(f"  {name:28} {count}")
    else:
        print("  -")

    print(
        "\nNOTE: resolved timing does not imply that every concrete occurrence time is known. "
        "Caller-active windows, runtime stack counts, and fixed-window spacing remain explicit inputs when the source does not provide them."
    )

    if unresolved:
        print("\nUNRESOLVED")
        for row in unresolved[: max(0, args.samples)]:
            print("\n----------------------------------------")
            print(
                f"rank={row.skill_rank_id} coef={row.coefficient_number} "
                f"ability={row.ability_id} name={row.ability_name}"
            )
            print(f"runtime_concerns={','.join(row.runtime_concerns)}")
            print(f"fragment={row.fragment}")
        return 1

    print("\nRESULT: PASS")
    print("Every current Phase 7 boundary row has explicit canonical timing semantics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
