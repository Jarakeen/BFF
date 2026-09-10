from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingService,
)


RUNTIME_EVIDENCE_TOLERANCE_SECONDS = 0.01


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect healer periodic-runtime candidate samples against canonical "
            "duration/cadence without approving or modifying evidence."
        )
    )
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=Path("data/eso.db"))
    parser.add_argument(
        "--tolerance",
        type=float,
        default=RUNTIME_EVIDENCE_TOLERANCE_SECONDS,
        help=(
            "seconds allowed when comparing observed cadence/expiry boundaries; "
            "defaults to the runtime observation service evidence tolerance"
        ),
    )
    return parser


def inspect_samples(
    candidate_path: str | Path,
    *,
    database_path: str | Path,
    tolerance_seconds: float = RUNTIME_EVIDENCE_TOLERANCE_SECONDS,
) -> tuple[dict, ...]:
    tolerance = float(tolerance_seconds)
    if tolerance < 0:
        raise ValueError("tolerance_seconds must be non-negative")

    path = Path(candidate_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("healer runtime observation candidate root must be an object")
    if str(payload.get("review_status") or "").strip().casefold() != "candidate":
        raise ValueError("inspection requires review_status='candidate'")

    samples = payload.get("samples")
    if not isinstance(samples, list):
        raise ValueError("healer runtime observation candidate samples must be a list")

    timing_service = RotationHealerCanonicalPeriodicTimingService(Path(database_path))
    rows: list[dict] = []
    for index, sample in enumerate(samples, start=1):
        if not isinstance(sample, dict):
            raise ValueError(f"sample {index}: entry must be an object")

        source_name = str(sample.get("source_name") or "").strip()
        coefficient_number = int(sample.get("coefficient_number"))
        activation = float(sample.get("activation_time_seconds"))
        ticks = tuple(float(value) for value in sample.get("observed_tick_times_seconds") or ())
        observation_end = float(sample.get("observation_end_seconds"))

        canonical = timing_service.resolve(
            source_name=source_name,
            coefficient_number=coefficient_number,
        )
        if not canonical.timing_ready_for_runtime_binding:
            rows.append(
                {
                    "sample_index": index,
                    "source_name": source_name,
                    "coefficient_number": coefficient_number,
                    "ready": False,
                    "unresolved": tuple(canonical.unresolved),
                }
            )
            continue

        assert canonical.duration_seconds is not None
        assert canonical.cadence_seconds is not None
        cadence = float(canonical.cadence_seconds)
        duration = float(canonical.duration_seconds)
        offsets = tuple(round(value - activation, 6) for value in ticks)
        intervals = tuple(
            round(ticks[position + 1] - ticks[position], 6)
            for position in range(len(ticks) - 1)
        )
        max_cadence_error = (
            max((abs(value - cadence) for value in intervals), default=0.0)
            if intervals
            else None
        )
        expiry = activation + duration
        expiry_delta = round(ticks[-1] - expiry, 6) if ticks else None
        observation_reaches_expiry = observation_end + tolerance >= expiry
        tick_on_expiry_boundary = (
            any(abs(value - expiry) <= tolerance for value in ticks)
            if observation_reaches_expiry
            else None
        )

        rows.append(
            {
                "sample_index": index,
                "source_name": source_name,
                "coefficient_number": coefficient_number,
                "ready": True,
                "canonical_duration_seconds": duration,
                "canonical_cadence_seconds": cadence,
                "observed_tick_count": len(ticks),
                "first_tick_offset_seconds": offsets[0] if offsets else None,
                "last_tick_offset_seconds": offsets[-1] if offsets else None,
                "max_cadence_error_seconds": (
                    round(max_cadence_error, 6)
                    if max_cadence_error is not None
                    else None
                ),
                "observation_reaches_expiry": observation_reaches_expiry,
                "tick_on_expiry_boundary": tick_on_expiry_boundary,
                "last_tick_to_expiry_seconds": expiry_delta,
            }
        )

    return tuple(rows)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = inspect_samples(
        args.candidate,
        database_path=args.db,
        tolerance_seconds=args.tolerance,
    )

    print("=" * 72)
    print(" PHASE 13 HEALER RUNTIME OBSERVATION CANDIDATE INSPECTION")
    print("=" * 72)
    print(f"Candidate: {args.candidate}")
    print(f"Database:  {args.db}")
    print(f"Tolerance: {args.tolerance:g}s")
    print(f"Samples:   {len(rows)}")
    print("Boundary:  read-only inspection; no sample is approved or promoted")
    print()

    for row in rows:
        prefix = (
            f"[{row['sample_index']:>2}] {row['source_name']} "
            f"coefficient {row['coefficient_number']}"
        )
        if not row["ready"]:
            print(prefix)
            print("     canonical timing: unresolved")
            for message in row["unresolved"]:
                print(f"     - {message}")
            continue

        expiry_state = (
            "yes" if row["tick_on_expiry_boundary"] is True
            else "no" if row["tick_on_expiry_boundary"] is False
            else "unknown"
        )
        cadence_error = row["max_cadence_error_seconds"]
        cadence_text = "n/a" if cadence_error is None else f"{cadence_error:g}s"
        print(prefix)
        print(
            "     canonical: "
            f"duration={row['canonical_duration_seconds']:g}s "
            f"cadence={row['canonical_cadence_seconds']:g}s"
        )
        print(
            "     observed:  "
            f"ticks={row['observed_tick_count']} "
            f"first=+{row['first_tick_offset_seconds']:g}s "
            f"last=+{row['last_tick_offset_seconds']:g}s "
            f"max_cadence_error={cadence_text}"
        )
        print(
            "     expiry:    "
            f"observed_through_boundary={row['observation_reaches_expiry']} "
            f"tick_on_boundary={expiry_state} "
            f"last_tick_delta={row['last_tick_to_expiry_seconds']:g}s"
        )

    print()
    print("Interpretation: this command describes candidate evidence only. Review and promotion remain explicit separate steps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
