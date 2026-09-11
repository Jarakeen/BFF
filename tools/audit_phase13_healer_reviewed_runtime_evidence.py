from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_healer_reviewed_runtime_evidence_loader import (
    RotationHealerReviewedRuntimeEvidenceLoader,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Load reviewed healer periodic timing plus reviewed refresh-policy evidence "
            "and print the composed runtime observations. Read-only; no evidence is promoted."
        )
    )
    parser.add_argument("--runtime-observations", type=Path, required=True)
    parser.add_argument("--refresh-policies", type=Path, default=None)
    parser.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = RotationHealerReviewedRuntimeEvidenceLoader(args.db).load(
        args.runtime_observations,
        refresh_fixture_path=args.refresh_policies,
    )

    print("=" * 76)
    print(" PHASE 13 HEALER REVIEWED RUNTIME EVIDENCE COMPOSITION AUDIT")
    print("=" * 76)
    print(f"Timing fixture:  {args.runtime_observations}")
    print(f"Refresh fixture: {args.refresh_policies or '(none)'}")
    print(f"Observations:    {len(result.observations)}")
    print("Boundary:        read-only composition; no candidate evidence is promoted")

    for observation in result.observations:
        refresh = observation.refresh_policy.value if observation.refresh_policy else "unresolved"
        first_tick = (
            f"+{float(observation.first_tick_offset_seconds):g}s"
            if observation.first_tick_offset_seconds is not None
            else "unresolved"
        )
        expiry = observation.tick_on_expiry_boundary
        expiry_text = "unresolved" if expiry is None else ("yes" if expiry else "no")
        print(
            f"- {observation.source_name} coefficient {observation.coefficient_number} "
            f"[{observation.game_version or 'unversioned'}]: "
            f"first_tick={first_tick} expiry_tick={expiry_text} refresh={refresh}"
        )

    if result.unresolved:
        print("Unresolved composition evidence:")
        for item in result.unresolved:
            print(f"  - {item}")
    else:
        print("Unresolved composition evidence: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
