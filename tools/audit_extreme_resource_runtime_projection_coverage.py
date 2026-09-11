from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_resource_runtime_projection_coverage_service import (
    ExtremeResourceRuntimeProjectionCoverageService,
)


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit proof-owned runtime/proc closure for Extreme max-resource objectives."
    )
    parser.add_argument("--database", default="data/eso.db")
    return parser


def main() -> int:
    args = _parser().parse_args()
    service = ExtremeResourceRuntimeProjectionCoverageService(Path(args.database))
    complete = True

    for objective in _OBJECTIVES:
        result = service.build(objective)
        print(f"\n{objective.upper()}")
        print(f"runtime_denominator_proven={result.runtime_denominator_proven}")
        print(f"skill_witness_denominator_proven={result.skill_witness_denominator_proven}")
        print(f"instantaneous_self_snapshot={result.instantaneous_self_snapshot}")
        print(f"projection_complete={result.projection_complete}")
        print("condition_markers=" + ", ".join(result.condition_markers))
        print("execution_owned_markers=" + ", ".join(result.execution_owned_markers))
        if result.unresolved:
            print("UNRESOLVED")
            for item in result.unresolved:
                print(f"  {item}")
        complete = complete and result.projection_complete

    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
