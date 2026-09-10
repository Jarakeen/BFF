from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.rotation_healer_periodic_observation_review_service import (
    RotationHealerPeriodicObservationReviewService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Promote explicitly reviewed healer periodic-runtime candidate samples into "
            "a separate reviewed fixture. Extraction alone never implies approval."
        )
    )
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--approve-sample",
        type=int,
        action="append",
        required=True,
        help="one-based candidate sample index explicitly reviewed and approved; repeat as needed",
    )
    parser.add_argument("--review-note", required=True)
    parser.add_argument("--reviewed-by", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidate = Path(args.candidate)
    output = Path(args.output)
    if candidate.resolve() == output.resolve():
        raise ValueError("reviewed healer runtime fixture must be written to a separate output path")

    service = RotationHealerPeriodicObservationReviewService()
    result = service.promote(
        candidate,
        approved_sample_indices=tuple(args.approve_sample),
        review_note=args.review_note,
        reviewed_by=args.reviewed_by,
    )
    service.write(result, output)

    print("PHASE 13 HEALER RUNTIME OBSERVATION REVIEW")
    print(f"Candidate: {candidate}")
    print(f"Reviewed:  {output}")
    print(
        "Approved sample indices: "
        + ", ".join(str(value) for value in result.approved_sample_indices)
    )
    print("Boundary: reviewed fixture is separate; candidate source was not modified")
    print("Refresh/recast semantics remain unresolved unless separately reviewed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
