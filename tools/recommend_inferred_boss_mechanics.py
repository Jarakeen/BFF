from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.boss_inferred_mechanic_recommendations import build_recommendations


def _source_dir() -> Path:
    candidates = (ROOT / "research" / "eso_info" / "bosses", ROOT / "data" / "eso_info" / "bosses")
    return next((path for path in candidates if path.exists()), candidates[-1])


def _has_content_records(root: Path) -> bool:
    return any(
        any((root / folder).glob("*.json"))
        for folder in ("trials", "dungeons", "arenas")
    )


def _content_root() -> Path:
    candidates = (ROOT / "research" / "eso_info", ROOT / "data" / "eso_info")
    return next((path for path in candidates if _has_content_records(path)), candidates[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend conservative review decisions for inferred boss mechanics.")
    parser.add_argument("--source-dir", type=Path, default=_source_dir())
    parser.add_argument("--content-root", type=Path, default=_content_root())
    parser.add_argument("--content-type", choices=("trial", "dungeon", "arena"), default="trial")
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

    print("\nRESULT: PASS")
    print("Read-only recommendation audit. No review manifest or canonical facts were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
