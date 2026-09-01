from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_text_evidence import extract_component_text_evidence
from tools.audit_phase6_component_gaps import load_phase6_gap_matrix

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class HealShieldCandidateRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    candidate_types: tuple[str, ...]
    resolved_effect_kind: str | None
    status: str
    phase3_reasons: tuple[str, ...]
    fragment: str


def load_heal_shield_candidates(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[HealShieldCandidateRow, ...]:
    rows: list[HealShieldCandidateRow] = []
    for gap in load_phase6_gap_matrix(database_path, limit=limit):
        candidate_types: list[str] = []
        if "healing_candidate" in gap.signals:
            candidate_types.append("heal")
        if "shield_candidate" in gap.signals:
            candidate_types.append("shield")
        if not candidate_types:
            continue

        evidence = extract_component_text_evidence(gap.fragment, gap.coefficient_number)
        resolved = evidence.effect_kind
        promoted = resolved in candidate_types
        rows.append(
            HealShieldCandidateRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                ability_name=gap.name,
                candidate_types=tuple(candidate_types),
                resolved_effect_kind=resolved,
                status="PROVABLE" if promoted else "UNRESOLVED",
                phase3_reasons=gap.phase3_reasons,
                fragment=gap.fragment,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[HealShieldCandidateRow, ...]) -> dict[str, object]:
    candidate_counts = Counter(kind for row in rows for kind in row.candidate_types)
    provable_counts = Counter(
        row.resolved_effect_kind
        for row in rows
        if row.status == "PROVABLE" and row.resolved_effect_kind is not None
    )
    return {
        "candidates": len(rows),
        "provable": sum(row.status == "PROVABLE" for row in rows),
        "unresolved": sum(row.status == "UNRESOLVED" for row in rows),
        "candidate_counts": candidate_counts,
        "provable_counts": provable_counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare Phase 6 heal/shield candidate signals with coefficient-aware text evidence."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_heal_shield_candidates(args.database, limit=args.limit)
    summary = summarize(rows)
    print("\n========================================")
    print(" PHASE 6 HEAL / SHIELD CANDIDATES")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {summary['candidates']}")
    print(f"Provable now:          {summary['provable']}")
    print(f"Still unresolved:      {summary['unresolved']}")

    print("\nCANDIDATE SIGNALS")
    for kind, count in summary["candidate_counts"].most_common():
        print(f"  {kind:28} {count}")
    print("\nPROVABLE EFFECT KINDS")
    for kind, count in summary["provable_counts"].most_common():
        print(f"  {kind:28} {count}")

    print("\nNOTE: PROVABLE means existing coefficient-aware text evidence already proves the effect kind.")
    print("This audit does not write classifications or promote mechanics.")

    ordered = sorted(rows, key=lambda row: (row.status != "UNRESOLVED", row.skill_rank_id, row.coefficient_number))
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"status={row.status}")
        print(f"candidate_types={','.join(row.candidate_types)}")
        print(f"resolved_effect_kind={row.resolved_effect_kind or '-'}")
        print(f"phase3_gap={','.join(row.phase3_reasons)}")
        if row.fragment:
            print(f"fragment={' '.join(row.fragment.split())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
