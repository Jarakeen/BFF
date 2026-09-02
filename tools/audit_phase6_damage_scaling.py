from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_damage_scaling import extract_explicit_component_damage_scaling
from minmax.skill_component_damage_scaling_repository import SkillComponentDamageScalingRepository
from minmax.skill_component_text_evidence import extract_component_text_evidence
from tools.audit_phase6_component_gaps import load_phase6_gap_matrix

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class DamageScalingAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    candidate_types: tuple[str, ...]
    promoted_types: tuple[str, ...]
    fragment: str

    @property
    def promoted(self) -> bool:
        return bool(self.promoted_types)


def load_damage_scaling_audit(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[DamageScalingAuditRow, ...]:
    path = Path(database_path)
    repository = SkillComponentDamageScalingRepository(path)
    rows: list[DamageScalingAuditRow] = []

    for gap in load_phase6_gap_matrix(path, limit=limit):
        evidence = extract_component_text_evidence(gap.fragment, gap.coefficient_number)
        if evidence.effect_kind != "damage" or not evidence.fragment:
            continue
        candidates = extract_explicit_component_damage_scaling(
            skill_rank_id=gap.skill_rank_id,
            coefficient_number=gap.coefficient_number,
            component_text=evidence.fragment,
        )
        if not candidates:
            continue
        promoted = repository.resolve(gap.skill_rank_id, gap.coefficient_number)
        rows.append(
            DamageScalingAuditRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                ability_name=gap.name,
                candidate_types=tuple(row.scaling_type.value for row in candidates),
                promoted_types=tuple(row.scaling_type.value for row in promoted),
                fragment=evidence.fragment,
            )
        )

    return tuple(rows)


def summarize(rows: tuple[DamageScalingAuditRow, ...]) -> dict[str, object]:
    promoted = [row for row in rows if row.promoted]
    return {
        "candidates": len(rows),
        "promoted": len(promoted),
        "unresolved": len(rows) - len(promoted),
        "types": Counter(kind for row in promoted for kind in row.promoted_types),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit explicit Phase 6 dynamic damage scaling against the real coefficient corpus."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_damage_scaling_audit(args.database, limit=args.limit)
    summary = summarize(rows)
    types: Counter[str] = summary["types"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 COMPONENT DAMAGE SCALING")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {summary['candidates']}")
    print(f"Canonically promoted:  {summary['promoted']}")
    print(f"Still unresolved:      {summary['unresolved']}")

    print("\nSCALING TYPES")
    for kind, count in types.most_common():
        print(f"  {kind:28} {count}")
    print("\nNOTE: tick number, accumulated damage, duration completion, and current state remain later-phase concerns.")

    ordered = sorted(rows, key=lambda row: (not row.promoted, row.skill_rank_id, row.coefficient_number))
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"status={'PROMOTED' if row.promoted else 'UNRESOLVED'}")
        print(f"candidate_types={','.join(row.candidate_types)}")
        print(f"promoted_types={','.join(row.promoted_types) or '-'}")
        print(f"fragment={' '.join(row.fragment.split())}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
