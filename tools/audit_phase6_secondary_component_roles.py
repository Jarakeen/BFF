from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_text_evidence import extract_component_text_evidence
from tools.audit_phase6_remaining_semantics import load_remaining_phase6_semantics

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class SecondaryComponentRoleAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    category: str
    effect_kind: str | None
    fragment: str


_ADDITIONAL_DAMAGE_RE = re.compile(
    r"\badditional(?:ly)?\b[^.;]{0,90}?\$(?P<number>\d+)(?!\d)[^.;]{0,50}?\bdamage\b",
    re.IGNORECASE,
)
_THEN_DAMAGE_RE = re.compile(
    r"\bthen\b[^.;]{0,90}?\$(?P<number>\d+)(?!\d)[^.;]{0,50}?\bdamage\b",
    re.IGNORECASE,
)
_ALSO_HEAL_RE = re.compile(
    r"\balso\b[^.;]{0,80}?\bheal(?:s|ed|ing)?\b[^.;]{0,60}?\$(?P<number>\d+)(?!\d)",
    re.IGNORECASE,
)
_ADDITIONAL_HEAL_RE = re.compile(
    r"\badditional(?:ly)?\b[^.;]{0,80}?\$(?P<number>\d+)(?!\d)(?:\s+health)?\b",
    re.IGNORECASE,
)
_TRIGGERED_ADDON_RE = re.compile(
    r"\b(?:causes?|causing|your\s+next|fully-charged|light\s+and\s+heavy\s+attacks?|heavy\s+attacks?)\b",
    re.IGNORECASE,
)
_ONCE_EVERY_RE = re.compile(r"\bonce\s+every\b", re.IGNORECASE)


def _numbers(pattern: re.Pattern[str], text: str) -> set[int]:
    return {int(match.group("number")) for match in pattern.finditer(text)}


def secondary_role_category(fragment: str, coefficient_number: int, effect_kind: str | None) -> str:
    text = " ".join(str(fragment or "").split())
    number = int(coefficient_number)

    if number in _numbers(_ADDITIONAL_DAMAGE_RE, text) and effect_kind == "damage":
        if _TRIGGERED_ADDON_RE.search(text) or _ONCE_EVERY_RE.search(text):
            return "phase7_triggered_additional_damage"
        return "explicit_additional_damage"
    if number in _numbers(_THEN_DAMAGE_RE, text) and effect_kind == "damage":
        return "explicit_followup_damage"
    if number in _numbers(_ALSO_HEAL_RE, text) and effect_kind == "heal":
        return "explicit_additional_heal"
    if number in _numbers(_ADDITIONAL_HEAL_RE, text) and effect_kind == "heal":
        return "explicit_additional_heal"
    if effect_kind in {"damage", "heal", "shield"}:
        return "classification_leftover"
    return "unresolved_secondary_signal"


def load_secondary_component_role_audit(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[SecondaryComponentRoleAuditRow, ...]:
    rows: list[SecondaryComponentRoleAuditRow] = []
    for item in load_remaining_phase6_semantics(database_path, limit=limit):
        if item.is_covered or "secondary_component_candidate" not in item.gap.signals:
            continue
        gap = item.gap
        evidence = extract_component_text_evidence(gap.fragment, gap.coefficient_number)
        rows.append(
            SecondaryComponentRoleAuditRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                ability_name=gap.name,
                category=secondary_role_category(gap.fragment, gap.coefficient_number, evidence.effect_kind),
                effect_kind=evidence.effect_kind,
                fragment=gap.fragment,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[SecondaryComponentRoleAuditRow, ...]) -> Counter[str]:
    return Counter(row.category for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit still-uncovered Phase 6 secondary-component signals by explicit component role."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=100)
    args = parser.parse_args()

    rows = load_secondary_component_role_audit(args.database, limit=args.limit)
    counts = summarize(rows)

    print("\n========================================")
    print(" PHASE 6 SECONDARY COMPONENT ROLES")
    print("========================================")
    print(f"Database: {args.database}")
    print(f"Rows:     {len(rows)}")
    print("\nCATEGORIES")
    for category, count in counts.most_common():
        print(f"  {category:32} {count}")
    print("\nNOTE: audit only; trigger/cadence semantics remain Phase 7 boundaries.")

    ordered = sorted(rows, key=lambda row: (row.category, row.skill_rank_id, row.coefficient_number))
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"category={row.category}")
        print(f"effect_kind={row.effect_kind or '-'}")
        print(f"fragment={' '.join(row.fragment.split())}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
