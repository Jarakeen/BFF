from __future__ import annotations

"""Stage a collected encounter-research ZIP into a reviewable JSON bundle."""

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.encounter_research_archive import import_research_archive, write_research_bundle


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract review candidates from user-collected encounter guides without "
            "modifying canonical encounter facts."
        )
    )
    parser.add_argument("archive", type=Path, help="Collected strategy/research ZIP file")
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "data" / "eso.db",
        help="Canonical ESO database used only for exact encounter identity resolution.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "encounter_research" / "strategy_archive_20260903_manifest.json",
        help="Optional source manifest with archive-member hashes/provenance hints.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "encounter_research" / "strategy_archive_20260903_review.json",
        help="Review bundle output path.",
    )
    args = parser.parse_args()

    bundle = import_research_archive(
        args.archive,
        args.database,
        manifest_path=args.manifest if args.manifest.exists() else None,
    )
    write_research_bundle(bundle, args.output)

    languages = Counter(row.language for row in bundle.sources if row.media_type != "image")
    event_types = Counter(row.event_type for row in bundle.candidates)
    encounters = Counter(row.encounter_id for row in bundle.candidates)

    print("ENCOUNTER RESEARCH ARCHIVE STAGING")
    print(f"Archive:   {args.archive}")
    print(f"Database:  {args.database}")
    print(f"Manifest:  {args.manifest if args.manifest.exists() else '(none)'}")
    print(f"Output:    {args.output}")
    print()
    print(f"Source records:       {len(bundle.sources)}")
    print(f"Visual sources:       {bundle.visual_sources}")
    print(f"Review candidates:    {len(bundle.candidates)}")
    print(f"Unmatched candidates: {bundle.unmatched_candidates}")
    print(f"Encounter matches:    {len(encounters)}")
    print()
    print("Languages:")
    for language, count in sorted(languages.items()):
        print(f"  {language:10} {count:5}")
    print("Candidate types:")
    for event_type, count in sorted(event_types.items()):
        print(f"  {event_type:12} {count:5}")
    print()
    print("Top matched encounters:")
    for encounter_id, count in encounters.most_common(15):
        print(f"  {encounter_id:40} {count:5}")
    print()
    print("RESULT: STAGED FOR REVIEW")
    print("No encounter_canonical_fact rows or canonical source JSON files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
