from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_text_evidence import extract_component_text_evidence
from tools.audit_skill_coefficient_slots import load_slot_audit
from tools.audit_skill_component_text_semantics import is_active_coefficient


DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class ImportGapRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    name: str
    reasons: tuple[str, ...]
    fragment: str
    effect_kind: str | None
    damage_type: str | None
    is_dot: bool | None
    is_aoe: bool | None


def _gap_reasons(evidence) -> tuple[str, ...]:
    if not evidence.fragment:
        return ("missing_fragment",)
    if evidence.effect_kind is None:
        return ("effect_kind",)

    reasons: list[str] = []
    if evidence.effect_kind == "damage":
        if evidence.damage_type is None:
            reasons.append("damage_type")
        if evidence.is_dot is None:
            reasons.append("periodicity")
        if evidence.is_aoe is None:
            reasons.append("target_shape")
    elif evidence.effect_kind == "heal":
        if evidence.is_dot is None:
            reasons.append("periodicity")
        if evidence.is_aoe is None:
            reasons.append("target_shape")
    elif evidence.effect_kind == "shield":
        # Damage-routing fields are not applicable to a shield. A proven shield
        # amount is therefore not considered unresolved merely because is_dot or
        # is_aoe is NULL.
        pass
    else:
        reasons.append("effect_kind")

    return tuple(reasons)


def load_import_gaps(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[ImportGapRow, ...]:
    rows = load_slot_audit(database_path, limit=limit)
    gaps: list[ImportGapRow] = []

    for row in rows:
        if not is_active_coefficient(row):
            continue
        if row.raw_slot_matches_coefficient is not True:
            gaps.append(
                ImportGapRow(
                    skill_rank_id=row.skill_rank_id,
                    coefficient_number=row.coefficient_number,
                    ability_id=row.ability_id,
                    name=row.name,
                    reasons=("slot_mismatch",),
                    fragment="",
                    effect_kind=None,
                    damage_type=None,
                    is_dot=None,
                    is_aoe=None,
                )
            )
            continue

        evidence = extract_component_text_evidence(
            row.coef_description,
            row.coefficient_number,
        )
        reasons = _gap_reasons(evidence)
        if not reasons:
            continue

        gaps.append(
            ImportGapRow(
                skill_rank_id=row.skill_rank_id,
                coefficient_number=row.coefficient_number,
                ability_id=row.ability_id,
                name=row.name,
                reasons=reasons,
                fragment=evidence.fragment,
                effect_kind=evidence.effect_kind,
                damage_type=evidence.damage_type,
                is_dot=evidence.is_dot,
                is_aoe=evidence.is_aoe,
            )
        )

    return tuple(gaps)


def summarize(rows: tuple[ImportGapRow, ...]) -> dict[str, object]:
    field_counts: Counter[str] = Counter()
    combination_counts: Counter[tuple[str, ...]] = Counter()
    for row in rows:
        combination_counts[row.reasons] += 1
        for reason in row.reasons:
            field_counts[reason] += 1
    return {
        "rows": len(rows),
        "field_counts": field_counts,
        "combination_counts": combination_counts,
    }


def sample_across_gap_combinations(
    rows: tuple[ImportGapRow, ...],
    limit: int,
) -> tuple[ImportGapRow, ...]:
    if limit <= 0:
        return ()

    grouped: dict[tuple[str, ...], deque[ImportGapRow]] = defaultdict(deque)
    for row in rows:
        grouped[row.reasons].append(row)

    ordered_groups = sorted(
        grouped,
        key=lambda reasons: (-len(grouped[reasons]), reasons),
    )
    selected: list[ImportGapRow] = []

    while ordered_groups and len(selected) < limit:
        next_groups: list[tuple[str, ...]] = []
        for reasons in ordered_groups:
            queue = grouped[reasons]
            if queue and len(selected) < limit:
                selected.append(queue.popleft())
            if queue:
                next_groups.append(reasons)
        ordered_groups = next_groups

    return tuple(selected)


def sample_gap_rows(
    rows: tuple[ImportGapRow, ...],
    limit: int,
) -> tuple[ImportGapRow, ...]:
    """Backward-compatible public name for diversified gap sampling."""
    return sample_across_gap_combinations(rows, limit)


def _clean(value: object, *, max_len: int = 280) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit why active skill coefficients fail deterministic component "
            "classification. Read-only; never modifies the database."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_import_gaps(args.database, limit=args.limit)
    summary = summarize(rows)
    field_counts: Counter[str] = summary["field_counts"]  # type: ignore[assignment]
    combination_counts: Counter[tuple[str, ...]] = summary["combination_counts"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 3 COMPONENT IMPORT GAP AUDIT")
    print("========================================")
    print(f"Database:               {args.database}")
    print(f"Unresolved active rows: {summary['rows']}")
    print()
    print("FIELD GAPS")
    for reason in (
        "missing_fragment",
        "slot_mismatch",
        "effect_kind",
        "damage_type",
        "periodicity",
        "target_shape",
    ):
        print(f"  {reason:18} {field_counts.get(reason, 0)}")

    print("\nCOMMON GAP COMBINATIONS")
    for reasons, count in combination_counts.most_common(12):
        label = ", ".join(reasons)
        print(f"  {count:5}  {label}")

    print("\nNOTE: counts overlap when one component is missing multiple required fields.")
    print("Non-applicable damage-routing fields are not counted as gaps for shields.")
    print("Samples are round-robin across gap combinations, not raw database order.")
    print("This audit is read-only and does not populate skill_component_classification.")

    sample_rows = sample_gap_rows(rows, max(0, args.samples))
    for row in sample_rows:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.name}"
        )
        print(f"missing={','.join(row.reasons)}")
        print(
            "semantic: "
            f"kind={row.effect_kind} damage_type={row.damage_type} "
            f"is_dot={row.is_dot} is_aoe={row.is_aoe}"
        )
        if row.fragment:
            print(f"fragment: {_clean(row.fragment)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
