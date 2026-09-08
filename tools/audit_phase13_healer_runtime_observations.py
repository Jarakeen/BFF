from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.rotation_healer_periodic_observation_fixture_service import (
    RotationHealerPeriodicObservationFixtureService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Review timestamp fixtures for healer periodic runtime facts without "
            "allowing observations to replace canonical cadence or duration."
        )
    )
    parser.add_argument(
        "--observations",
        required=True,
        help="JSON fixture containing reviewed activation/tick timestamps",
    )
    parser.add_argument(
        "--db",
        default="data/eso.db",
        help="canonical ESO database path (default: data/eso.db)",
    )
    return parser


def render_report(report) -> str:
    lines = [
        "================================================================",
        " PHASE 13 HEALER RUNTIME OBSERVATION AUDIT",
        "================================================================",
        f"Fixture: {report.source_path}",
        f"Schema:  {report.schema_version}",
        "Boundary: observations may prove micro-timing; canonical cadence/duration remain authoritative",
        "",
    ]

    if not report.entries:
        lines.append("No valid observation entries were loaded.")

    for index, entry in enumerate(report.entries, start=1):
        canonical = entry.canonical
        observed = entry.observed
        lines.extend(
            [
                f"[{index}] {entry.sample.source_name} coefficient {entry.sample.coefficient_number}",
                f"  canonical cadence:  {canonical.cadence_seconds:g}s" if canonical.cadence_seconds is not None else "  canonical cadence:  unresolved",
                f"  canonical duration: {canonical.duration_seconds:g}s" if canonical.duration_seconds is not None else "  canonical duration: unresolved",
                f"  activation:         {entry.sample.activation_time_seconds:g}s",
                "  observed ticks:     "
                + (
                    ", ".join(f"{value:g}s" for value in entry.sample.observed_tick_times_seconds)
                    if entry.sample.observed_tick_times_seconds
                    else "none"
                ),
                f"  observation end:    {entry.sample.observation_end_seconds:g}s",
            ]
        )
        if observed.observation is None:
            lines.append("  promotable runtime observation: no")
        else:
            observation = observed.observation
            lines.extend(
                [
                    "  promotable runtime observation: yes",
                    f"    first tick offset: +{observation.first_tick_offset_seconds:g}s",
                    "    tick on expiry:    "
                    + ("yes" if observation.tick_on_expiry_boundary else "no"),
                    "    refresh policy:    unresolved",
                ]
            )
        if observed.evidence:
            lines.append("  evidence:")
            lines.extend(f"    - {item}" for item in observed.evidence)
        if observed.unresolved:
            lines.append("  unresolved:")
            lines.extend(f"    - {item}" for item in observed.unresolved)
        lines.append("")

    lines.extend(["REPORT UNRESOLVED", "-----------------"])
    if report.unresolved:
        lines.extend(f"- {item}" for item in report.unresolved)
    else:
        lines.append("none")

    lines.extend(
        [
            "",
            "Interpretation: a promotable observation can fill first-tick and expiry-boundary facts; repeated-application refresh semantics still require a separate reviewed recast observation.",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = RotationHealerPeriodicObservationFixtureService(Path(args.db))
    report = service.load(Path(args.observations))
    print(render_report(report))
    return 0 if not report.unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
