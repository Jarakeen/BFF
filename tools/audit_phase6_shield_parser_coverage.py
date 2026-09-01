from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_text_evidence import extract_component_text_evidence
from tools.audit_phase6_heal_shield_unresolved_taxonomy import load_unresolved_taxonomy

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class ShieldCoverageRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    status: str
    resolved_effect_kind: str | None
    fragment: str


def load_shield_parser_coverage(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[ShieldCoverageRow, ...]:
    rows: list[ShieldCoverageRow] = []
    for candidate in load_unresolved_taxonomy(database_path, limit=limit):
        if "shield" not in candidate.candidate_types:
            continue
        if candidate.category == "modifier_mention":
            continue

        evidence = extract_component_text_evidence(
            candidate.fragment,
            candidate.coefficient_number,
        )
        rows.append(
            ShieldCoverageRow(
                skill_rank_id=candidate.skill_rank_id,
                coefficient_number=candidate.coefficient_number,
                ability_id=candidate.ability_id,
                ability_name=candidate.ability_name,
                status="PROVABLE" if evidence.effect_kind == "shield" else "UNRESOLVED",
                resolved_effect_kind=evidence.effect_kind,
                fragment=candidate.fragment,
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit remaining Phase 6 shield candidates against coefficient-aware parser coverage."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_shield_parser_coverage(args.database, limit=args.limit)
    provable = sum(row.status == "PROVABLE" for row in rows)

    print("\n========================================")
    print(" PHASE 6 SHIELD PARSER COVERAGE")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {len(rows)}")
    print(f"Provable now:          {provable}")
    print(f"Still unresolved:      {len(rows) - provable}")
    print("\nNOTE: modifier mentions are excluded; this audit promotes no classifications.")

    ordered = sorted(rows, key=lambda row: (row.status != "UNRESOLVED", row.skill_rank_id, row.coefficient_number))
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"status={row.status}")
        print(f"resolved_effect_kind={row.resolved_effect_kind or '-'}")
        print(f"fragment={' '.join(row.fragment.split())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
