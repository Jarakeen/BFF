from __future__ import annotations

"""Diagnose the final Phase 6 closeout blockers without promoting mechanics."""

import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_phase6_closeout import load_phase6_closeout

DEFAULT_DATABASE = ROOT / "data" / "eso.db"
_COLOR_FIELDS = (
    "name",
    "description",
    "coef_description",
    "raw_description",
    "raw_tooltip",
    "raw_json",
)


def _normalize(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _table_columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})")}


def _ability_source_fields(database_path: Path, ability_id: int) -> dict[str, str]:
    with sqlite3.connect(database_path) as db:
        if db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ability'"
        ).fetchone() is None:
            return {}
        columns = _table_columns(db, "ability")
        fields = [field for field in _COLOR_FIELDS if field in columns]
        if not fields:
            return {}
        row = db.execute(
            "SELECT " + ", ".join(fields) + " FROM ability WHERE ability_id = ?",
            (int(ability_id),),
        ).fetchone()
        if row is None:
            return {}
    return {
        field: _normalize(value)
        for field, value in zip(fields, row)
        if _normalize(value)
    }


def _review_family(reason: str, signals: tuple[str, ...], fragment: str) -> str:
    lower = fragment.casefold()
    if "trigger relationship" in reason or "conditional/temporal" in reason:
        return "static_trigger_or_condition"
    if "duration/cadence" in reason:
        return "duration_or_cadence_relationship"
    if "utility_relationship_candidate" in reason:
        return "utility_relationship"
    if "stored_damage_scaling" in reason or "per_tick_damage_ramp" in reason:
        return "damage_scaling"
    if "damage_scaling_or_modifier_candidate" in reason:
        return "damage_modifier_or_scaling"
    if "conditional_or_temporal_candidate" in reason:
        return "static_trigger_or_condition"
    if "execute" in lower or "health" in lower and any(token in lower for token in ("below", "under", "less than")):
        return "execute_or_health_condition"
    if "conditional_candidate" in signals or "temporal_proc_candidate" in signals:
        return "static_trigger_or_condition"
    return "other_phase6_review"


def summarize(database_path: str | Path) -> dict[str, object]:
    path = Path(database_path)
    rows = load_phase6_closeout(path)
    blockers = [
        row
        for row in rows
        if row.closeout_status in {"NEEDS_PHASE6_REVIEW", "SOURCE_EVIDENCE_BLOCKED"}
    ]
    review = [row for row in blockers if row.closeout_status == "NEEDS_PHASE6_REVIEW"]
    source = [row for row in blockers if row.closeout_status == "SOURCE_EVIDENCE_BLOCKED"]
    families = Counter(_review_family(row.reason, row.signals, row.fragment) for row in review)
    reasons = Counter(row.reason for row in review)
    return {
        "rows": rows,
        "blockers": blockers,
        "review": review,
        "source": source,
        "families": families,
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Group final Phase 6 closeout blockers and inspect source-blocked ability fields."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--samples", type=int, default=80)
    args = parser.parse_args()

    path = Path(args.database)
    summary = summarize(path)
    blockers = summary["blockers"]
    review = summary["review"]
    source = summary["source"]
    families: Counter[str] = summary["families"]  # type: ignore[assignment]
    reasons: Counter[str] = summary["reasons"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 CLOSEOUT BLOCKERS")
    print("========================================")
    print(f"Database:                 {path}")
    print(f"Total blockers:           {len(blockers)}")
    print(f"Needs Phase 6 review:     {len(review)}")
    print(f"Source-evidence blocked:  {len(source)}")

    print("\nREVIEW FAMILY")
    for name, count in families.most_common():
        print(f"  {name:34} {count}")

    print("\nREVIEW REASON")
    for name, count in reasons.most_common():
        print(f"  {name:64} {count}")

    grouped: dict[str, list[object]] = defaultdict(list)
    for row in review:
        grouped[_review_family(row.reason, row.signals, row.fragment)].append(row)

    remaining = max(0, int(args.samples))
    for family, family_rows in grouped.items():
        if remaining <= 0:
            break
        print(f"\n=== {family} ({len(family_rows)}) ===")
        for row in family_rows[:remaining]:
            print("\n----------------------------------------")
            print(
                f"rank={row.skill_rank_id} coef={row.coefficient_number} "
                f"ability={row.ability_id} name={row.ability_name}"
            )
            print(f"reason={row.reason}")
            if row.signals:
                print(f"signals={','.join(row.signals)}")
            print(f"fragment={row.fragment}")
            remaining -= 1
            if remaining <= 0:
                break

    if source:
        print("\n========================================")
        print(" SOURCE-EVIDENCE BLOCKERS")
        print("========================================")
        seen: set[int] = set()
        for row in source:
            print("\n----------------------------------------")
            print(
                f"rank={row.skill_rank_id} coef={row.coefficient_number} "
                f"ability={row.ability_id} name={row.ability_name}"
            )
            print(f"reason={row.reason}")
            print(f"fragment={row.fragment or '<empty>'}")
            if row.ability_id in seen:
                print("source_fields=(same ability as above)")
                continue
            seen.add(row.ability_id)
            fields = _ability_source_fields(path, row.ability_id)
            if not fields:
                print("source_fields=<none>")
                continue
            for field, value in fields.items():
                print(f"ability.{field}: {value}")

    print("\nNOTE: diagnostic only. No classifications or mechanics are written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
