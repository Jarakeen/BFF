from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_phase6_component_gaps import semantic_signals
from tools.audit_phase6_heal_shield_unresolved_taxonomy import unresolved_category
from tools.audit_skill_component_text_semantics import build_semantic_audit

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
    """Audit shield-signaled active components independently of gap status.

    This deliberately scans the active coefficient corpus instead of starting
    from the unresolved gap matrix. Otherwise a parser improvement makes a
    successfully resolved shield disappear from the audit denominator.
    Modifier-only wording such as damage-shield-strength changes is excluded.
    """

    rows: list[ShieldCoverageRow] = []
    for component in build_semantic_audit(database_path, limit=limit):
        if not component.active_coefficient:
            continue
        if component.raw_slot_matches is not True:
            continue
        fragment = component.text.fragment
        if not fragment or "shield_candidate" not in semantic_signals(fragment):
            continue
        if unresolved_category(fragment, component.coefficient_number) == "modifier_mention":
            continue

        effect_kind = component.text.effect_kind
        rows.append(
            ShieldCoverageRow(
                skill_rank_id=component.skill_rank_id,
                coefficient_number=component.coefficient_number,
                ability_id=component.ability_id,
                ability_name=component.name,
                status="PROVABLE" if effect_kind == "shield" else "NON_SHIELD_COMPONENT",
                resolved_effect_kind=effect_kind,
                fragment=fragment,
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Phase 6 shield-signaled active components against coefficient-aware parser coverage."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_shield_parser_coverage(args.database, limit=args.limit)
    provable = sum(row.status == "PROVABLE" for row in rows)
    non_shield = sum(row.status == "NON_SHIELD_COMPONENT" for row in rows)

    print("\n========================================")
    print(" PHASE 6 SHIELD PARSER COVERAGE")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Shield-signaled rows:  {len(rows)}")
    print(f"Provable shields:      {provable}")
    print(f"Non-shield components: {non_shield}")
    print("\nNOTE: modifier mentions are excluded; non-shield rows retain a neighboring shield mention.")
    print("This audit scans active coefficients directly and promotes no classifications.")

    ordered = sorted(
        rows,
        key=lambda row: (row.status != "NON_SHIELD_COMPONENT", row.skill_rank_id, row.coefficient_number),
    )
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
