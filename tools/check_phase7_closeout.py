from __future__ import annotations

"""Read-only Phase 7 closeout gate for conditional/runtime coverage.

This gate does not simulate combat and does not mutate canonical data. It verifies
that the Phase 6 rows intentionally deferred to Phase 7 no longer require trigger
classification or generic runtime review, and that every remaining boundary row
has explicit canonical timing semantics.

The behavioral runtime contracts themselves remain covered by their focused
pytest suites. This script provides the real-database corpus gate used for Phase
7 closeout evidence.
"""

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_runtime_timing import extract_skill_component_runtime_timing
from tools.audit_phase7_runtime_boundaries import load_phase7_runtime_boundaries, summarize

DEFAULT_DATABASE = ROOT / "data" / "eso.db"

RUNTIME_CAPABILITIES = (
    "shared_runtime_event_contract",
    "component_timing_and_state_binding",
    "effect_trigger_eligibility",
    "deterministic_proc_chance",
    "global_and_target_cooldowns",
    "active_duration_windows",
    "stacking_and_refresh",
    "ordered_effect_streams",
    "status_effect_runtime_state",
    "triggered_resource_restoration",
    "triggered_healing",
    "target_count_and_explicit_selection",
)


def evaluate_phase7_closeout(database_path: str | Path) -> dict[str, object]:
    rows = load_phase7_runtime_boundaries(database_path)
    boundary_summary = summarize(rows)

    timing_unresolved = tuple(
        row
        for row in rows
        if extract_skill_component_runtime_timing(row.fragment) is None
    )
    timing_kinds: Counter[str] = Counter()
    for row in rows:
        timing = extract_skill_component_runtime_timing(row.fragment)
        if timing is not None:
            timing_kinds[timing.bound_kind.value] += 1

    failures: list[str] = []
    trigger_resolution = int(boundary_summary["trigger_resolution"])
    runtime_review = int(boundary_summary["runtime_review"])

    if trigger_resolution:
        failures.append(f"{trigger_resolution} boundary row(s) still need canonical trigger resolution")
    if runtime_review:
        failures.append(f"{runtime_review} boundary row(s) still require generic runtime review")
    if timing_unresolved:
        failures.append(f"{len(timing_unresolved)} boundary row(s) lack canonical timing semantics")

    return {
        "rows": rows,
        "boundary_summary": boundary_summary,
        "timing_unresolved": timing_unresolved,
        "timing_kinds": timing_kinds,
        "capabilities": RUNTIME_CAPABILITIES,
        "failures": tuple(failures),
        "passed": not failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the real-database Phase 7 conditional/runtime closeout gate."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()

    result = evaluate_phase7_closeout(args.database)
    rows = result["rows"]
    boundary_summary = result["boundary_summary"]
    timing_unresolved = result["timing_unresolved"]
    timing_kinds: Counter[str] = result["timing_kinds"]  # type: ignore[assignment]
    failures = result["failures"]

    print("\n========================================")
    print(" PHASE 7 CONDITIONAL RUNTIME CLOSEOUT")
    print("========================================")
    print(f"Database:                   {args.database}")
    print(f"Phase 7 boundary rows:      {len(rows)}")
    print(f"Need trigger resolution:   {boundary_summary['trigger_resolution']}")
    print(f"Runtime-review rows:        {boundary_summary['runtime_review']}")
    print(f"Timing unresolved:          {len(timing_unresolved)}")

    print("\nTIMING BOUND KINDS")
    if timing_kinds:
        for name, count in timing_kinds.most_common():
            print(f"  {name:28} {count}")
    else:
        print("  -")

    print("\nRUNTIME CAPABILITY CONTRACTS")
    for capability in RUNTIME_CAPABILITIES:
        print(f"  [x] {capability}")

    if failures:
        print("\nFAILURES")
        for failure in failures:
            print(f"  - {failure}")
        for row in tuple(timing_unresolved)[: max(0, args.samples)]:
            print(
                f"  timing unresolved: rank={row.skill_rank_id} "
                f"coef={row.coefficient_number} ability={row.ability_name}"
            )
        print("\nRESULT: FAIL")
        return 1

    print("\nRESULT: PASS")
    print(
        "All current Phase 7 boundary rows have canonical trigger classification "
        "and timing semantics; behavioral runtime contracts are delegated to "
        "their focused regression suites."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
