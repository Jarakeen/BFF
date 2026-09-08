from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.build_model import PlayerBuild
from services.rotation_healer_component_identity_gap_service import (
    RotationHealerComponentIdentityGapService,
)

DEFAULT_DATABASE = ROOT / "data" / "eso.db"
DEFAULT_BUILDS = ROOT / "data" / "builds.json"


def _load_build(path: Path, build_name: str, character_name: str | None) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    target_build = str(build_name or "").strip().casefold()
    target_character = str(character_name or "").strip().casefold()
    matches: list[PlayerBuild] = []
    for member in payload.get("Members", []):
        if str(member.get("BuildName", "") or "").strip().casefold() != target_build:
            continue
        if target_character and str(member.get("Name", "") or "").strip().casefold() != target_character:
            continue
        matches.append(PlayerBuild.from_dict(member))
    if not matches:
        raise ValueError(f"saved build not found: character={character_name!r} build={build_name!r}")
    if len(matches) > 1:
        raise ValueError(f"saved build name is ambiguous: {build_name!r}; supply --character")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit a real saved healer build for missing canonical HEAL/PERIODIC component identity. "
            "Coefficient-local tooltip text is diagnostic evidence only and never writes canonical data."
        )
    )
    parser.add_argument("--build", required=True)
    parser.add_argument("--character")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--builds", default=str(DEFAULT_BUILDS))
    args = parser.parse_args()

    build = _load_build(Path(args.builds), args.build, args.character)
    report = RotationHealerComponentIdentityGapService(args.database).inspect(build)

    print("=" * 68)
    print(" PHASE 13 HEALER COMPONENT IDENTITY GAP AUDIT")
    print("=" * 68)
    print(f"Character: {report.character_name or 'unnamed'}")
    print(f"Build:     {report.build_name or 'unnamed'}")
    print("Boundary:  audit/review candidates only; tooltip text does not become canonical automatically")
    print()

    if not report.rows:
        print("No canonical or coefficient-text healing components were identified on the saved bars.")
    else:
        for row in report.rows:
            print(
                f"[{row.bar} slot {row.slot}] {row.skill_name} "
                f"rank_id={row.skill_rank_id} ability_id={row.ability_id} coefficient={row.coefficient_number}"
            )
            print(
                "  canonical: "
                f"kind={row.canonical_effect_kind.value} "
                f"temporal={row.canonical_heal_temporal_scope.value if row.canonical_heal_temporal_scope else 'unresolved'} "
                f"is_dot={row.canonical_is_dot}"
            )
            print(
                "  coefficient text: "
                f"kind={row.text_evidence.effect_kind or 'unresolved'} "
                f"periodic={row.text_evidence.is_dot}"
            )
            if row.text_evidence.fragment:
                print(f"  fragment: {row.text_evidence.fragment}")
            flags: list[str] = []
            if row.needs_heal_identity_review:
                flags.append("HEAL identity review")
            if row.needs_periodic_identity_review:
                flags.append("PERIODIC heal identity review")
            print("  review: " + (", ".join(flags) if flags else "none"))
            print()

    print("REVIEW CANDIDATES")
    print("-----------------")
    if report.review_candidates:
        for row in report.review_candidates:
            flags: list[str] = []
            if row.needs_heal_identity_review:
                flags.append("heal")
            if row.needs_periodic_identity_review:
                flags.append("periodic")
            print(
                f"- {row.skill_name}: rank_id={row.skill_rank_id} coefficient={row.coefficient_number} "
                f"missing={'+'.join(flags)}"
            )
    else:
        print("none")

    print()
    print("UNRESOLVED")
    print("----------")
    if report.unresolved:
        for item in report.unresolved:
            print(f"- {item}")
    else:
        print("none")

    print()
    print(
        "Interpretation: a review candidate means coefficient-local text supports healing identity that "
        "the persisted canonical classification does not yet expose. Review the exact rank/coefficient "
        "before adding an overlay; do not infer runtime tick or refresh rules from this audit."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
