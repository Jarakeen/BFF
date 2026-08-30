from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from minmax.skill_component_text_evidence import (
    SkillComponentTextEvidence,
    extract_component_text_evidence,
)
from tools.audit_skill_coefficient_slots import (
    CoefficientSlotAuditRow,
    load_slot_audit,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class ComponentSemanticAuditRow:
    skill_rank_id: int
    ability_id: int
    name: str
    coefficient_number: int
    coefficient_type: str
    active_coefficient: bool
    raw_slot_matches: bool | None
    text: SkillComponentTextEvidence


def is_active_coefficient(row: CoefficientSlotAuditRow) -> bool:
    """Return False only for UESP's exact empty coefficient-slot marker."""

    return not (
        str(row.coefficient_type or "").strip() == "-1"
        and float(row.a) == -1.0
        and float(row.b) == -1.0
        and float(row.c) == -1.0
        and float(row.r) == -1.0
    )


def build_semantic_audit(
    database_path: str | Path,
    *,
    skill_rank_id: int | None = None,
    ability_id: int | None = None,
    limit: int | None = None,
) -> tuple[ComponentSemanticAuditRow, ...]:
    rows = load_slot_audit(
        database_path,
        skill_rank_id=skill_rank_id,
        ability_id=ability_id,
        limit=limit,
    )

    results: list[ComponentSemanticAuditRow] = []
    for row in rows:
        active = is_active_coefficient(row)
        evidence = (
            extract_component_text_evidence(
                row.coef_description,
                row.coefficient_number,
            )
            if active
            else SkillComponentTextEvidence(
                coefficient_number=row.coefficient_number,
                fragment="",
                evidence=("inactive coefficient slot",),
            )
        )
        results.append(
            ComponentSemanticAuditRow(
                skill_rank_id=row.skill_rank_id,
                ability_id=row.ability_id,
                name=row.name,
                coefficient_number=row.coefficient_number,
                coefficient_type=row.coefficient_type,
                active_coefficient=active,
                raw_slot_matches=row.raw_slot_matches_coefficient,
                text=evidence,
            )
        )
    return tuple(results)


def summarize(rows: tuple[ComponentSemanticAuditRow, ...]) -> dict[str, int]:
    active = [row for row in rows if row.active_coefficient]
    return {
        "rows": len(rows),
        "active": len(active),
        "inactive": len(rows) - len(active),
        "active_with_fragment": sum(bool(row.text.fragment) for row in active),
        "effect_kind": sum(row.text.effect_kind is not None for row in active),
        "damage_type": sum(row.text.damage_type is not None for row in active),
        "periodicity": sum(row.text.is_dot is not None for row in active),
        "area_shape": sum(row.text.is_aoe is not None for row in active),
        "crit": sum(row.text.can_crit is not None for row in active),
    }


def _clean(value: object, *, max_len: int = 320) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit explicit per-coefficient semantics from UESP coefficient-aware "
            "tooltip text. Read-only; does not populate classification tables."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--skill-rank-id", type=int)
    parser.add_argument("--ability-id", type=int)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Print active coefficient slots only.",
    )
    args = parser.parse_args()

    rows = build_semantic_audit(
        args.database,
        skill_rank_id=args.skill_rank_id,
        ability_id=args.ability_id,
        limit=args.limit,
    )
    counts = summarize(rows)

    print("\n========================================")
    print(" PHASE 3 COMPONENT TEXT SEMANTICS AUDIT")
    print("========================================")
    print(f"Database:             {args.database}")
    print(f"Coefficient rows:     {counts['rows']}")
    print(f"Active coefficients:  {counts['active']}")
    print(f"Inactive slots:       {counts['inactive']}")
    print(f"Active text fragment: {counts['active_with_fragment']}")
    print(f"Effect kind evidence: {counts['effect_kind']}")
    print(f"Damage type evidence: {counts['damage_type']}")
    print(f"Periodic/direct:      {counts['periodicity']}")
    print(f"AoE/single target:    {counts['area_shape']}")
    print(f"Crit eligibility:     {counts['crit']}")
    print()
    print("NOTE: only explicit wording near $N in coef_description is extracted.")
    print("raw_description placeholder numbers are not treated as coefficient numbers.")
    print("Critical eligibility remains unresolved unless another verified source proves it.")

    printable = [row for row in rows if row.active_coefficient or not args.active_only]
    for row in printable[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.name}"
        )
        print(
            f"active={row.active_coefficient} type={row.coefficient_type} "
            f"raw_slot_match={row.raw_slot_matches}"
        )
        if not row.active_coefficient:
            print("semantic: inactive coefficient slot")
            continue
        print(
            "semantic: "
            f"kind={row.text.effect_kind} damage_type={row.text.damage_type} "
            f"is_dot={row.text.is_dot} is_aoe={row.text.is_aoe} "
            f"can_crit={row.text.can_crit}"
        )
        print(f"fragment: {_clean(row.text.fragment)}")
        for evidence in row.text.evidence:
            print(f"  evidence: {evidence}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
