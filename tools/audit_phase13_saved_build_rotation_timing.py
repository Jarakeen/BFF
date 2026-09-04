from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.saved_build_rotation_timing_audit import audit_saved_build_rotation_timing
from models.build_model import PlayerBuild


def _load_build(path: Path, build_name: str, character_name: str | None = None) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    members = payload.get("Members", [])
    target_build = str(build_name or "").strip().casefold()
    target_character = str(character_name or "").strip().casefold()

    matches: list[PlayerBuild] = []
    for member in members:
        candidate_build = str(member.get("BuildName", "") or "").strip()
        candidate_character = str(member.get("Name", "") or "").strip()
        if candidate_build.casefold() != target_build:
            continue
        if target_character and candidate_character.casefold() != target_character:
            continue
        matches.append(PlayerBuild.from_dict(member))

    if not matches:
        if target_character:
            raise ValueError(
                f"Saved build not found: character={character_name!r} build={build_name!r}"
            )
        raise ValueError(f"Saved build not found: {build_name}")
    if len(matches) > 1:
        raise ValueError(
            f"Saved build name is ambiguous: {build_name!r}; supply --character"
        )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Phase 13 canonical duration evidence for a real saved build"
    )
    parser.add_argument("--build", required=True)
    parser.add_argument("--character")
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--builds", default=str(ROOT / "data" / "builds.json"))
    args = parser.parse_args()

    build = _load_build(Path(args.builds), args.build, args.character)
    audit = audit_saved_build_rotation_timing(
        build,
        database_path=Path(args.database),
    )

    print("=" * 58)
    print(" PHASE 13 SAVED-BUILD ROTATION TIMING EVIDENCE AUDIT")
    print("=" * 58)
    print(f"Character:      {audit.character_name or 'unnamed'}")
    print(f"Build:          {audit.build_name or 'unnamed'}")
    print(f"Role:           {audit.role or 'unresolved'}")
    print("Boundary:       duration evidence only; not a rotation recommendation")
    print()

    for bar in ("front", "back"):
        print(f"{bar.upper()} BAR")
        print("-" * len(f"{bar.upper()} BAR"))
        bar_skills = [item for item in audit.skills if item.bar == bar]
        if not bar_skills:
            print("none")
            print()
            continue

        for item in bar_skills:
            label = "ultimate" if item.kind.value == "ultimate" else "skill"
            print(f"[{item.slot}] {item.skill_name} ({label})")
            if item.duration_resolution.ability_id is not None:
                print(f"    ability id: {item.duration_resolution.ability_id}")
            durations = item.canonical_durations_seconds
            if durations:
                print(
                    "    canonical durations: "
                    + ", ".join(f"{value:g}s" for value in durations)
                )
                for evidence in item.duration_resolution.evidence:
                    condition = f" condition={evidence.condition}" if evidence.condition else ""
                    print(
                        f"      - {evidence.effect_name}: {evidence.duration_seconds:g}s "
                        f"source={evidence.source}{condition}"
                    )
            else:
                print("    canonical durations: none")
        print()

    print("UNRESOLVED")
    print("----------")
    if audit.unresolved:
        for item in audit.unresolved:
            print(item)
    else:
        print("none")

    print()
    print(
        "Interpretation: durations are canonical evidence exposed by existing effect data. "
        "No recast interval, priority, or healer/DD rotation policy is inferred here."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
