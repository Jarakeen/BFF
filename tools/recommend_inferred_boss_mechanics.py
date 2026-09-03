from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.boss_inferred_mechanic_decisions import apply_accepted_recommendations
from services.boss_inferred_mechanic_recommendations import build_recommendations


def _source_dir() -> Path:
    candidates = (ROOT / "research" / "eso_info" / "bosses", ROOT / "data" / "eso_info" / "bosses")
    for path in candidates:
        if any(path.glob("*.json")):
            return path
    return candidates[-1]


def _content_root() -> Path:
    candidates = (ROOT / "research" / "eso_info", ROOT / "data" / "eso_info")
    for path in candidates:
        if any((path / folder).glob("*.json") for folder in ("trials", "dungeons", "arenas")):
            return path
    return candidates[-1]


def _manifest() -> Path:
    return ROOT / "data" / "encounter_reviews" / "inferred_boss_mechanics.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend conservative review decisions for inferred boss mechanics.")
    parser.add_argument("--source-dir", type=Path, default=_source_dir())
    parser.add_argument("--content-root", type=Path, default=_content_root())
    parser.add_argument("--content-type", choices=("trial", "dungeon", "arena"), default="trial")
    parser.add_argument("--manifest", type=Path, default=_manifest())
    parser.add_argument(
        "--apply-accepted",
        action="store_true",
        help="Change only pending manifest rows whose conservative recommendation is accepted.",
    )
    parser.add_argument("--samples", type=int, default=30)
    args = parser.parse_args()

    recommendations = build_recommendations(
        args.source_dir,
        args.content_root,
        content_type=args.content_type,
    )
    accepted = [row for row in recommendations if row.recommended_status == "accepted"]
    pending = [row for row in recommendations if row.recommended_status == "pending"]

    print("=" * 72)
    print(" INFERRED BOSS MECHANIC RECOMMENDATIONS")
    print("=" * 72)
    print(f"Content type:                  {args.content_type}")
    print(f"Mechanics in batch:            {len(recommendations)}")
    print(f"Recommended accepted:          {len(accepted)}")
    print(f"Remain pending:                {len(pending)}")
    print("Recommended rejected:          0")

    if accepted:
        print("\nSAFE ACCEPTANCE CANDIDATES")
        for item in accepted[: max(0, args.samples)]:
            print(f"  - {item.row.encounter_id} :: {item.row.mechanic_name} | {item.rationale}")

    if pending:
        print("\nPENDING SAMPLE")
        for item in pending[: max(0, args.samples)]:
            unclear = ", ".join(
                support.field for support in item.field_support if support.status != "supported"
            )
            print(f"  - {item.row.encounter_id} :: {item.row.mechanic_name} | review={unclear}")

    if args.apply_accepted:
        if not args.manifest.exists():
            print(f"\nRESULT: BLOCKED\nReview manifest does not exist: {args.manifest}")
            return 1
        try:
            changed = apply_accepted_recommendations(args.manifest, recommendations)
        except (OSError, ValueError) as exc:
            print(f"\nRESULT: BLOCKED\nUnable to apply recommendations: {exc}")
            return 1
        print(f"\nManifest accepted rows changed: {changed}")
        print(f"Manifest:                       {args.manifest}")
        print("No canonical encounter facts were changed.")

    print("\nRESULT: PASS")
    if not args.apply_accepted:
        print("Read-only recommendation audit. No review manifest or canonical facts were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
