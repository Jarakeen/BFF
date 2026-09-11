from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_resource_runtime_coverage_audit_service import (
    ExtremeResourceRuntimeCoverageAuditService,
)


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit remaining runtime/proc blockers for Extreme max-resource objectives."
    )
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument(
        "--objective",
        action="append",
        choices=_OBJECTIVES,
        help="Limit the audit to one or more objectives. Defaults to all three.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    objectives = tuple(args.objective or _OBJECTIVES)
    service = ExtremeResourceRuntimeCoverageAuditService(Path(args.database))
    all_complete = True

    for objective in objectives:
        audit = service.build(objective)
        all_complete = all_complete and audit.projection_complete
        print(f"\n{objective.upper()}")
        print(f"contextual_passives_reviewed={len(audit.contextual_passives_reviewed)}")
        print(f"conditional_gear_effects={len(audit.conditional_gear_effects)}")
        print(f"denominator_proven={audit.denominator_proven}")
        print(f"projection_complete={audit.projection_complete}")
        print("condition_markers=" + (", ".join(audit.condition_markers) or "none"))
        if audit.conditional_gear_effects:
            print("CONDITIONAL GEAR EFFECTS:")
            for row in audit.conditional_gear_effects:
                print(
                    f"  {row.set_name} [{row.piece_count}] | {row.stat} {row.value:g} | "
                    f"condition={row.condition}"
                )
        if audit.unresolved:
            print("UNRESOLVED:")
            for item in audit.unresolved:
                print(f"  {item}")

    return 0 if all_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
