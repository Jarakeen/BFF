from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.rotation_ability_priority import AbilityPriorityList
from services.rotation_horizon_displacement_provenance_quality_service import (
    RotationHorizonDisplacementProvenanceQualityService,
)
from services.rotation_priority_displacement_provenance_replay_service import (
    RotationPriorityDisplacementProvenanceReplayService,
)
from tools.audit_phase13_dd_priority_schedule import _character_name, _priority_entries
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify saved-DD fixed-horizon displacement spillover with shared priority "
            "evidence plus diagnostic queue-instance replay provenance."
        )
    )
    parser.add_argument("--character")
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument(
        "--priority",
        action="append",
        default=[],
        metavar="BAR:SLOT:PRIORITY",
        help="Rank every occupied ordinary saved-bar slot; lower number is higher priority.",
    )
    args = parser.parse_args()

    duration = float(args.duration)
    if duration <= 0:
        raise ValueError("duration must be positive")

    build = _load_build(Path(args.builds), args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in _DD_ROLE_KEYS:
        raise ValueError(
            "DD horizon quality audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    priorities = _priority_entries(tuple(args.priority or ()), build=build)
    priority_list = AbilityPriorityList(
        character_name=_character_name(build),
        build_name=str(getattr(build, "BuildName", "") or "").strip(),
        role=str(getattr(build, "Role", "") or "Unspecified").strip(),
        entries=priorities,
    )
    request = RotationGenerationRequest(
        duration_seconds=duration,
        weave_light_attacks=True,
        ability_priorities=priorities,
    )
    support = RotationGenerationSupport()
    generated = support.generate_with_evidence(build=build, request=request)

    definition = support.build_definition(build=build, request=request)
    seed_plan = support.planner.build_plan(definition, build)
    seed_projection = support.duration_refinement.duration_analysis.analyze(seed_plan)
    normalized_seed = support.duration_refinement.persistent_toggle_plan.normalize(
        seed_plan,
        duration_rules=seed_projection.rules,
        priorities=priority_list,
    ).plan
    replay = RotationPriorityDisplacementProvenanceReplayService().replay(
        seed_plan=normalized_seed,
        rules=seed_projection.rules,
        priorities=priority_list,
    )

    production_horizon = tuple(
        item
        for item in generated.plan.unresolved
        if " was displaced beyond the " in str(item or "")
    )
    replay_horizon = tuple(
        item
        for item in replay.plan.unresolved
        if " was displaced beyond the " in str(item or "")
    )
    replay_matches_production = production_horizon == replay_horizon
    provenance = replay.spillovers if replay_matches_production else ()

    report = RotationHorizonDisplacementProvenanceQualityService().classify(
        generated.plan,
        priorities=priority_list,
        spillover_provenance=provenance,
    )

    counts = Counter(row.quality.value for row in report.rows)
    print("=" * 72)
    print(" PHASE 13 DD HORIZON DISPLACEMENT QUALITY AUDIT")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Duration:  {duration:g}s")
    print(f"Spillover rows: {len(report.rows)}")
    print(f"Proven cadence debt: {len(report.cadence_debt)}")
    print(f"Clean of proven cadence debt: {report.clean_of_proven_cadence_debt}")
    print(f"Replay horizon diagnostics identical: {replay_matches_production}")
    print()

    print("CLASSIFICATION COUNTS")
    print("---------------------")
    for key in (
        "protected_obligation_saturation",
        "ordinary_cadence_debt",
        "late_window_truncation",
        "deduplicated_queue_saturation",
        "unknown_provenance",
    ):
        print(f"{key}={counts.get(key, 0)}")
    print()

    print("SPILLOVER DETAIL")
    print("----------------")
    if not report.rows:
        print("none")
    for row in report.rows:
        displaced_from = (
            f"{row.displaced_from_time_seconds:g}s"
            if row.displaced_from_time_seconds is not None
            else "unknown"
        )
        ordinary = (
            ",".join(f"{value:g}" for value in row.later_ordinary_skill_times)
            if row.later_ordinary_skill_times
            else "none"
        )
        print(
            f"{row.bar} | priority={row.priority} | {row.skill_name} | "
            f"displaced_from={displaced_from} | quality={row.quality.value} | "
            f"later_ordinary={ordinary}"
        )
        if row.plausible_instances:
            sources = ", ".join(
                f"{item.source_time_seconds:g}s/seq{item.source_sequence}"
                for item in row.plausible_instances
            )
            print(f"  plausible_sources: {sources}")
        print(f"  reason: {row.reason}")
    print()

    if not replay_matches_production:
        print(
            "NEXT_STEP=replay diverged from production horizon diagnostics; do not use replay provenance until the generation-path mismatch is explained"
        )
    elif report.cadence_debt:
        print(
            "NEXT_STEP=proven ordinary cadence debt remains; inspect those exact post-displacement ordinary slots before changing refresh policy"
        )
    elif counts.get("unknown_provenance", 0):
        print(
            "NEXT_STEP=no proven cadence debt, but genuinely unknown provenance remains; inspect only those rows"
        )
    else:
        print(
            "NEXT_STEP=no proven ordinary cadence debt and no unknown horizon provenance remains; fixed-window spillover does not justify a scheduler rewrite"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
