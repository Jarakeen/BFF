from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.encounter_capability_candidate_audit import EncounterCapabilityCandidateAudit


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Discover Phase 10 encounter-capability candidates for human review. "
            "Text matches are review hints only and are never promoted automatically."
        )
    )
    parser.add_argument(
        "capability",
        choices=EncounterCapabilityCandidateAudit.supported_capabilities(),
        help="Encounter capability to investigate.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="ESO reference database.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    audit = EncounterCapabilityCandidateAudit(args.database)
    rows = audit.candidates(args.capability)

    print("PHASE 10 ENCOUNTER CAPABILITY CANDIDATES")
    print(f"Capability: {args.capability}")
    print(f"Database:   {args.database}")
    print(f"Candidates: {len(rows)}")
    print()
    print("REVIEW ONLY: text matches are not canonical capability mappings.")

    for row in rows:
        print()
        print(f"Ability {row.ability_id}: {row.ability_name}")
        print(
            "  canonical identity: "
            f"base={row.base_ability_id if row.base_ability_id is not None else '(unknown)'}"
            f" | morph={row.morph if row.morph is not None else '(unknown)'}"
            f" | rank={row.rank if row.rank is not None else '(unknown)'}"
        )
        print(
            "  taxonomy: "
            f"class={row.class_type or '(none)'} | skill_line={row.skill_line or '(none)'}"
        )
        print(f"  matched: {row.matched_term!r} in {row.matched_field}")
        print(f"  source text: {row.matched_source_text}")
        print(
            "  resolved EffectVariant names: "
            + (", ".join(row.resolved_effect_names) if row.resolved_effect_names else "(none)")
        )
        print(
            "  resolved sources: "
            + (", ".join(row.resolved_effect_sources) if row.resolved_effect_sources else "(none)")
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
