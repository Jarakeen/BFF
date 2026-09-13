from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_detonating_siphon_controlled_spatial_evidence_service import (
    RotationDetonatingSiphonControlledSpatialEvidenceService,
    RotationDetonatingSiphonControlledSpatialSample,
)


def load_samples(path: Path) -> tuple[RotationDetonatingSiphonControlledSpatialSample, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("samples") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError("controlled spatial evidence file must contain a samples array")

    samples: list[RotationDetonatingSiphonControlledSpatialSample] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"sample {index} must be an object")
        try:
            samples.append(
                RotationDetonatingSiphonControlledSpatialSample(
                    label=str(row["label"]),
                    caster=tuple(row["caster"]),
                    corpse_candidate=tuple(row["corpse_candidate"]),
                    target=tuple(row["target"]),
                    damage_observed=bool(row["damage_observed"]),
                )
            )
        except KeyError as exc:
            raise ValueError(f"sample {index} is missing required field {exc.args[0]!r}") from exc
    return tuple(samples)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Research-only analyzer for controlled Detonating Siphon spatial hit/no-hit "
            "samples. It compares endpoint-circle hypotheses and derives corridor bounds; "
            "it does not modify production mechanics."
        )
    )
    parser.add_argument(
        "samples",
        type=Path,
        help="JSON file containing controlled spatial samples",
    )
    parser.add_argument(
        "--circle-radius",
        type=float,
        default=5.0,
        help="Circle radius used for endpoint hypothesis comparison. Defaults to 5.0.",
    )
    args = parser.parse_args()

    try:
        samples = load_samples(args.samples)
        report = RotationDetonatingSiphonControlledSpatialEvidenceService().analyze(
            samples,
            circle_radius=args.circle_radius,
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print("=" * 72)
    print(" DETONATING SIPHON CONTROLLED SPATIAL EVIDENCE")
    print("=" * 72)
    print(f"Sample file: {args.samples}")
    print(f"Samples: {report.sample_count}")
    print(f"Circle comparison radius: {args.circle_radius:g}")
    print()
    print("Endpoint-circle hypotheses:")
    print(
        f"- caster-centered: {report.caster_circle.matching_samples}/{report.sample_count} matching"
    )
    if report.caster_circle.conflicting_samples:
        print("  conflicts: " + ", ".join(report.caster_circle.conflicting_samples))
    print(
        f"- corpse-centered: {report.corpse_circle.matching_samples}/{report.sample_count} matching"
    )
    if report.corpse_circle.conflicting_samples:
        print("  conflicts: " + ", ".join(report.corpse_circle.conflicting_samples))
    print()
    print("Corridor evidence:")
    print(
        "- minimum half-width required by observed hits: "
        + _fmt(report.hit_sample_minimum_segment_half_width)
    )
    print(
        "- upper half-width bound from interior no-hit samples: "
        + _fmt(report.no_hit_segment_upper_bound)
    )
    print(f"- non-overlapping corridor interval resolved: {report.corridor_width_resolved}")

    if report.unresolved:
        print("\nUnresolved:")
        for message in report.unresolved:
            print(f"- {message}")

    print("\nInterpretation guardrails:")
    print("- This is research evidence only; it does not write production geometry.")
    print("- A circle-hypothesis conflict can still be explained by the independent tether.")
    print("- Promote no mechanic until sample identity, units, and repeatability are reviewed.")
    return 0 if not report.unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
