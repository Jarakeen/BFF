from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.build_model import PlayerBuild
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerPeriodicRuntimeEvidenceService,
)
from services.rotation_healer_saved_build_periodic_timing_service import (
    RotationHealerSavedBuildPeriodicTimingEntry,
    RotationHealerSavedBuildPeriodicTimingService,
)

DEFAULT_DATABASE = ROOT / "data" / "eso.db"
DEFAULT_BUILDS = ROOT / "data" / "builds.json"


def _load_build(path: Path, build_name: str, character_name: str | None) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    members = payload.get("Members", [])
    target_build = str(build_name or "").strip().casefold()
    target_character = str(character_name or "").strip().casefold()

    matches: list[PlayerBuild] = []
    for member in members:
        if str(member.get("BuildName", "") or "").strip().casefold() != target_build:
            continue
        if target_character and str(member.get("Name", "") or "").strip().casefold() != target_character:
            continue
        matches.append(PlayerBuild.from_dict(member))

    if not matches:
        raise ValueError(
            f"saved build not found: character={character_name!r} build={build_name!r}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"saved build name is ambiguous: {build_name!r}; supply --character"
        )
    return matches[0]


def runtime_facts_still_required(entry: RotationHealerSavedBuildPeriodicTimingEntry) -> tuple[str, ...]:
    """Facts still needed before a repeated rotation can emit authoritative HoT ticks.

    The audit delegates the actual readiness decision to the same runtime-evidence
    bridge the rotation engine uses. This renderer only turns those precise
    diagnostics into compact human labels.
    """

    resolution = RotationHealerPeriodicRuntimeEvidenceService().resolve(
        canonical=entry.timing,
        observation=None,
        repeated_applications=True,
    )
    messages = tuple(item.casefold() for item in resolution.unresolved)
    gaps: list[str] = []

    if any("canonical periodic cadence" in item for item in messages):
        gaps.append("periodic cadence")
    if any("canonical active duration" in item for item in messages):
        gaps.append("active duration")
    if any("first-tick offset" in item for item in messages):
        gaps.append("first-tick offset from cast/application")
    if any("tick-at-expiry" in item for item in messages):
        gaps.append("tick-at-expiry boundary behavior")
    if any("refresh/recast" in item for item in messages):
        gaps.append("refresh/recast behavior for repeated applications")

    return tuple(dict.fromkeys(gaps))


def _render_entry(entry: RotationHealerSavedBuildPeriodicTimingEntry) -> list[str]:
    timing = entry.timing
    lines = [
        f"[{entry.bar} slot {entry.slot}] {entry.skill_name} coefficient {entry.coefficient_number}",
        f"  cadence:  {timing.cadence_seconds:g}s" if timing.cadence_seconds is not None else "  cadence:  unresolved",
        f"  duration: {timing.duration_seconds:g}s" if timing.duration_seconds is not None else "  duration: unresolved",
        (
            f"  bound:    {timing.timing.bound_kind.value}"
            if timing.timing is not None
            else "  bound:    unresolved"
        ),
        f"  canonical timing ready: {'yes' if timing.timing_ready_for_runtime_binding else 'no'}",
    ]
    if timing.evidence:
        lines.append("  evidence:")
        lines.extend(f"    - {item}" for item in timing.evidence)
    if timing.unresolved:
        lines.append("  canonical unresolved:")
        lines.extend(f"    - {item}" for item in timing.unresolved)
    lines.append("  runtime facts still required:")
    gaps = runtime_facts_still_required(entry)
    if gaps:
        lines.extend(f"    - {item}" for item in gaps)
    else:
        lines.append("    - none")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit a real saved healer build for periodic-heal runtime readiness. "
            "Reports canonical cadence/duration separately from first-tick and refresh semantics."
        )
    )
    parser.add_argument("--build", required=True)
    parser.add_argument("--character")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--builds", default=str(DEFAULT_BUILDS))
    args = parser.parse_args()

    build = _load_build(Path(args.builds), args.build, args.character)
    report = RotationHealerSavedBuildPeriodicTimingService(args.database).inspect(build)

    print("=" * 64)
    print(" PHASE 13 HEALER PERIODIC RUNTIME READINESS AUDIT")
    print("=" * 64)
    print(f"Character: {report.character_name or 'unnamed'}")
    print(f"Build:     {report.build_name or 'unnamed'}")
    print("Boundary:  evidence/readiness only; not HPS, survival, or a recast recommendation")
    print()

    if not report.entries:
        print("No slotted periodic-heal components were canonically identified.")
    else:
        for entry in report.entries:
            for line in _render_entry(entry):
                print(line)
            print()

    print("REPORT UNRESOLVED")
    print("-----------------")
    if report.unresolved:
        for item in report.unresolved:
            print(f"- {item}")
    else:
        print("none")

    print()
    print(
        "Interpretation: cadence and duration can be canonical while full rotation tick "
        "scheduling remains blocked by first-occurrence, expiry-boundary, or refresh evidence."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
