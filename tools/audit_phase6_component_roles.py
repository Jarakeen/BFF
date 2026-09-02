from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_role_repository import SkillComponentRoleRepository
from minmax.skill_component_text_evidence import extract_component_text_evidence
from tools.audit_phase6_component_gaps import load_phase6_gap_matrix
from tools.audit_phase6_secondary_component_roles import secondary_role_category

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class ComponentRoleAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    candidate_role: str
    promoted_roles: tuple[str, ...]
    fragment: str

    @property
    def promoted(self) -> bool:
        return bool(self.promoted_roles)


def load_component_role_audit(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[ComponentRoleAuditRow, ...]:
    path = Path(database_path)
    repository = SkillComponentRoleRepository(path)
    rows: list[ComponentRoleAuditRow] = []

    for gap in load_phase6_gap_matrix(path, limit=limit):
        if "secondary_component_candidate" not in gap.signals:
            continue
        evidence = extract_component_text_evidence(gap.fragment, gap.coefficient_number)
        category = secondary_role_category(gap.fragment, gap.coefficient_number, evidence.effect_kind)
        if category not in {"explicit_additional_damage", "explicit_additional_heal"}:
            continue
        roles = repository.resolve(gap.skill_rank_id, gap.coefficient_number)
        rows.append(
            ComponentRoleAuditRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                ability_name=gap.name,
                candidate_role=(
                    "additional_damage"
                    if category == "explicit_additional_damage"
                    else "additional_heal"
                ),
                promoted_roles=tuple(role.role_type.value for role in roles),
                fragment=" ".join(str(gap.fragment or "").split()),
            )
        )

    return tuple(rows)


def summarize(rows: tuple[ComponentRoleAuditRow, ...]) -> dict[str, object]:
    promoted = [row for row in rows if row.promoted]
    return {
        "candidates": len(rows),
        "promoted": len(promoted),
        "unresolved": len(rows) - len(promoted),
        "roles": Counter(role for row in promoted for role in row.promoted_roles),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit explicit Phase 6 same-ability component roles against the real coefficient corpus."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=60)
    args = parser.parse_args()

    rows = load_component_role_audit(args.database, limit=args.limit)
    summary = summarize(rows)
    roles: Counter[str] = summary["roles"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 COMPONENT ROLES")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {summary['candidates']}")
    print(f"Canonically promoted:  {summary['promoted']}")
    print(f"Still unresolved:      {summary['unresolved']}")

    print("\nROLE TYPES")
    for role, count in roles.most_common():
        print(f"  {role:28} {count}")

    print("\nNOTE: trigger timing, cadence, and activation windows remain Phase 7 concerns.")

    ordered = sorted(rows, key=lambda row: (not row.promoted, row.skill_rank_id, row.coefficient_number))
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"status={'PROMOTED' if row.promoted else 'UNRESOLVED'}")
        print(f"candidate_role={row.candidate_role}")
        print(f"promoted_roles={','.join(row.promoted_roles) or '-'}")
        print(f"fragment={row.fragment}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
