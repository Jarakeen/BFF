from __future__ import annotations

"""Verify observed Elder Dragon Blood heals against the 50%-linear wound hypothesis.

Provide at least two --sample values as CURRENT,MAX,HEAL. This tool does not alter
canonical combat math; it only reports whether observations support the historical
hypothesis ``base * (1 + 0.5 * missing_health_fraction)`` closely enough to justify
further review.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_elder_dragon_blood_wound_curve_service import (
    ElderDragonBloodWoundSample,
    ExtremeElderDragonBloodWoundCurveService,
)


def _parse_sample(raw: str) -> ElderDragonBloodWoundSample:
    parts = [part.strip() for part in str(raw or "").split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("sample must be CURRENT,MAX,HEAL")
    try:
        current, maximum, heal = (float(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("sample values must be numeric") from exc
    return ElderDragonBloodWoundSample(
        current_health=current,
        max_health=maximum,
        observed_heal=heal,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample",
        action="append",
        required=True,
        type=_parse_sample,
        help="Observed cast as CURRENT,MAX,HEAL; repeat at least twice",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Maximum relative error allowed to call the linear hypothesis supported (default 0.01 = 1%%)",
    )
    args = parser.parse_args()

    try:
        result = ExtremeElderDragonBloodWoundCurveService().verify(
            tuple(args.sample),
            relative_tolerance=args.tolerance,
        )
    except ValueError as exc:
        parser.error(str(exc))

    print("=============================================")
    print(" ELDER DRAGON BLOOD WOUND-CURVE AUDIT")
    print("=============================================")
    print(f"Samples: {result.sample_count}")
    print(f"Fitted base heal: {result.fitted_base_heal:.3f}")
    print(f"Max relative error: {result.max_relative_error:.4%}")
    print(f"RMS relative error: {result.root_mean_square_relative_error:.4%}")
    print(
        "50%-linear hypothesis supported: "
        + ("YES" if result.linear_half_missing_health_supported else "NO")
    )
    print("\nOBSERVATIONS")
    for index, (sample, predicted) in enumerate(zip(args.sample, result.predicted_heals), 1):
        missing = sample.missing_health_fraction
        error = abs(predicted - sample.observed_heal) / sample.observed_heal
        print(
            f"[{index:02d}] health {sample.current_health:.0f}/{sample.max_health:.0f} "
            f"({missing:.1%} missing) | observed {sample.observed_heal:.3f} | "
            f"predicted {predicted:.3f} | error {error:.4%}"
        )

    print("\nBoundary: empirical verifier only; canonical Elder Dragon Blood math remains unchanged.")
    return 0 if result.linear_half_missing_health_supported else 3


if __name__ == "__main__":
    raise SystemExit(main())
