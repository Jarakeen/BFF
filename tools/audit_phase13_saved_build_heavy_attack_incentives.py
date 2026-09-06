from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from minmax.healer_heavy_attack_build_discovery import (
    discover_healer_heavy_attack_build_incentives,
)
from services.build_service import BuildService


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit static Phase 13 heavy-attack incentives for one saved build."
    )
    parser.add_argument("--character", required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    args = parser.parse_args()

    roster = BuildService(args.builds).load()
    selected = None
    for build in roster.Members:
        if _character_name(build) != args.character:
            continue
        if str(getattr(build, "BuildName", "") or "").strip() != args.build:
            continue
        selected = build
        break

    if selected is None:
        raise SystemExit(
            f"Saved build not found: character={args.character!r}, build={args.build!r}"
        )

    incentives = discover_healer_heavy_attack_build_incentives(selected)

    print("==============================================================")
    print(" PHASE 13 SAVED-BUILD HEAVY ATTACK INCENTIVE AUDIT")
    print("==============================================================")
    print(f"Character: {args.character}")
    print(f"Build:     {args.build}")
    print(f"Class:     {getattr(selected, 'EsoClass', '') or 'Unspecified'}")
    print()

    if not incentives:
        print("No static heavy-attack incentives resolved from the saved build.")
        return 0

    for item in incentives:
        print(f"{item.bar.title()} | {item.weapon.value} | {item.kind.value} | {item.name}")
        if item.recurrence_seconds is not None:
            print(f"  Recurrence evidence: {item.recurrence_seconds:g}s")
        if item.maximum_effect_duration_seconds is not None:
            print(f"  Max effect duration: {item.maximum_effect_duration_seconds:g}s")
        if item.requires_active_effect:
            print(f"  Runtime condition: {item.requires_active_effect} must be active")
        print(f"  Source: {item.source}")

    print()
    print("Boundary: static incentives are not scheduled heavies; runtime safety, uptime,")
    print("resource state, refresh collisions, and exact channel timing still gate each cast.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
