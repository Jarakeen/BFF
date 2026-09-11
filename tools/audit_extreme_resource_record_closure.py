from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_record_result import ExtremeRecordProofStatus
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
)


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")
_COMPLETE_BOUNDARY = (
    "All dynamic axes in this record's declared search universe are covered by "
    "searched or proof-owned denominator evidence."
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit final-record closure for Extreme max-resource objectives."
    )
    parser.add_argument("--database", default="data/eso.db")
    return parser


def main() -> int:
    args = _parser().parse_args()
    service = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        database_path=Path(args.database)
    )
    complete = True

    for objective in _OBJECTIVES:
        record = service.record(objective)
        boundary = next(
            (
                row
                for row in record.explanation
                if row.startswith("Residual unproven search axes:")
                or row == _COMPLETE_BOUNDARY
            ),
            "",
        )
        objective_complete = bool(
            record.proof_status is ExtremeRecordProofStatus.PROVEN
            and record.search_coverage.complete
            and record.globally_proven
            and not record.search_coverage.omitted
            and not record.unresolved
            and boundary == _COMPLETE_BOUNDARY
        )

        print(f"\n{objective.upper()}")
        print(f"raw_value={record.raw_value}")
        print(f"proof_status={record.proof_status.value}")
        print(f"coverage_denominator_proven={record.search_coverage.denominator_proven}")
        print(f"coverage_complete={record.search_coverage.complete}")
        print(f"globally_proven={record.globally_proven}")
        print(f"omitted={', '.join(record.search_coverage.omitted)}")
        print(f"unresolved={', '.join(record.unresolved)}")
        print(f"residual_boundary={boundary}")
        print(f"record_closure_complete={objective_complete}")
        complete = complete and objective_complete

    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
