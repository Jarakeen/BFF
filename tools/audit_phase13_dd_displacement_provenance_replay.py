from __future__ import annotations

"""Replay saved-DD priority scheduling and recover displaced action-instance origins."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.rotation_ability_priority import AbilityPriorityList
from services.rotation_priority_displacement_provenance_replay_service import (
    RotationPriorityDisplacementProvenanceReplayService,
)
from tools.audit_phase13_dd_priority_schedule import _character_name, _priority_entries
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
            "DD provenance replay requires a saved damage-dealer build; "
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
    production = support.generate_with_evidence(build=build, request=request).plan

    production_horizon = tuple(
        item
        for item in production.unresolved
        if " was displaced beyond the " in str(item or "")
    )
    replay_horizon = tuple(
        item
        for item in replay.plan.unresolved
        if " was displaced beyond the " in str(item or "")
    )

    print("=" * 72)
    print(" PHASE 13 DD DISPLACEMENT PROVENANCE REPLAY")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Duration:  {duration:g}s")
    print(f"Queue decisions observed: {len(replay.decisions)}")
    print(f"Production horizon tails: {len(production_horizon)}")
    print(f"Replay horizon tails:     {len(replay_horizon)}")
    print(f"Horizon diagnostics identical: {production_horizon == replay_horizon}")
    print()

    print("SPILLOVER INSTANCE PROVENANCE")
    print("-----------------------------")
    resolved_count = 0
    for row in replay.spillovers:
        if row.resolved:
            resolved_count += 1
            print(
                f"{row.bar} | {row.skill_name} | source={row.source_time_seconds:g}s "
                f"sequence={row.source_sequence} | last_seen_queued={row.last_observed_queue_time_seconds:g}s"
            )
        else:
            last_seen = (
                "unknown"
                if row.last_observed_queue_time_seconds is None
                else f"{row.last_observed_queue_time_seconds:g}s"
            )
            print(f"{row.bar} | {row.skill_name} | source=unknown | last_seen_queued={last_seen}")
            for message in row.unresolved:
                print(f"  unresolved: {message}")
    print()

    unresolved_count = len(replay.spillovers) - resolved_count
    print("SUMMARY")
    print("-------")
    print(f"resolved_spillover_instances={resolved_count}")
    print(f"unresolved_spillover_instances={unresolved_count}")
    if not production_horizon == replay_horizon:
        print(
            "NEXT_STEP=replay diverged from production horizon diagnostics; do not use provenance until generation-path mismatch is explained"
        )
    elif unresolved_count:
        print(
            "NEXT_STEP=some tails still enter outside the observable queue-selection seam; add narrower provenance only for those exact cases"
        )
    else:
        print(
            "NEXT_STEP=all horizon tails have exact seed-instance provenance; feed these origins into the quality audit without changing scheduler policy"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
