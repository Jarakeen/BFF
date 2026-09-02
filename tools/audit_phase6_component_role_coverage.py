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
class ComponentRoleCoverageRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    disposition: str
    signals: tuple[str, ...]
    audit_category: str
    repository_roles: tuple[str, ...]
    fragment: str

    @property
    def status(self) -> str:
        if self.audit_category in {"explicit_additional_damage", "explicit_additional_heal"}:
            return "AUDITED_CANDIDATE"
        return "EXTRA_REPOSITORY_MATCH"


def load_component_role_coverage(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[ComponentRoleCoverageRow, ...]:
    path = Path(database_path)
    repository = SkillComponentRoleRepository(path)
    rows: list[ComponentRoleCoverageRow] = []

    for gap in load_phase6_gap_matrix(path, limit=limit):
        roles = repository.resolve(gap.skill_rank_id, gap.coefficient_number)
        if not roles:
            continue
        evidence = extract_component_text_evidence(gap.fragment, gap.coefficient_number)
        category = secondary_role_category(
            gap.fragment,
            gap.coefficient_number,
            evidence.effect_kind,
        )
        rows.append(
            ComponentRoleCoverageRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                ability_name=gap.name,
                disposition=gap.disposition,
                signals=gap.signals,
                audit_category=category,
                repository_roles=tuple(role.role_type.value for role in roles),
                fragment=" ".join(str(gap.fragment or "").split()),
            )
        )

    return tuple(rows)


def summarize(rows: tuple[ComponentRoleCoverageRow, ...]) -> dict[str, object]:
    return {
        "resolved": len(rows),
        "statuses": Counter(row.status for row in rows),
        "roles": Counter(role for row in rows for role in row.repository_roles),
        "extra_categories": Counter(
            row.audit_category for row in rows if row.status == "EXTRA_REPOSITORY_MATCH"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare every Phase 6 gap row resolved by the component-role repository "
            "against the stable fragment-level role candidate audit."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=100)
    args = parser.parse_args()

    rows = load_component_role_coverage(args.database, limit=args.limit)
    summary = summarize(rows)
    statuses: Counter[str] = summary["statuses"]  # type: ignore[assignment]
    roles: Counter[str] = summary["roles"]  # type: ignore[assignment]
    extra_categories: Counter[str] = summary["extra_categories"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 COMPONENT ROLE COVERAGE")
    print("========================================")
    print(f"Database:                {args.database}")
    print(f"Repository-resolved rows:{summary['resolved']:>5}")

    print("\nSTATUS")
    for name, count in statuses.most_common():
        print(f"  {name:28} {count}")

    print("\nROLE TYPES")
    for name, count in roles.most_common():
        print(f"  {name:28} {count}")

    if extra_categories:
        print("\nEXTRA MATCH AUDIT CATEGORIES")
        for name, count in extra_categories.most_common():
            print(f"  {name:28} {count}")

    print(
        "\nNOTE: EXTRA_REPOSITORY_MATCH means the full canonical description resolved "
        "a role that the fragment-level candidate audit did not independently flag."
    )

    ordered = sorted(
        rows,
        key=lambda row: (row.status != "EXTRA_REPOSITORY_MATCH", row.skill_rank_id, row.coefficient_number),
    )
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"status={row.status}")
        print(f"audit_category={row.audit_category}")
        print(f"repository_roles={','.join(row.repository_roles)}")
        print(f"disposition={row.disposition}")
        if row.signals:
            print(f"signals={','.join(row.signals)}")
        if row.fragment:
            print(f"fragment={row.fragment}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
