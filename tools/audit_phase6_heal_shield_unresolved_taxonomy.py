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

from tools.audit_phase6_heal_shield_candidates import load_heal_shield_candidates

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class UnresolvedHealShieldRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    category: str
    candidate_types: tuple[str, ...]
    resolved_effect_kind: str | None
    fragment: str


_DAMAGE_LINKED_HEAL_RE = re.compile(
    r"\bheal(?:ing|s|ed)?\b[^.;]{0,80}\b(?:damage\s+(?:dealt|done|caused)|of\s+the\s+damage)\b",
    flags=re.IGNORECASE,
)
_MISSING_HEALTH_HEAL_RE = re.compile(
    r"\bheal(?:ing|s|ed)?\b[^.;]{0,80}\b\d+(?:\.\d+)?\s*%\s+of\s+(?:your|their|the\s+target(?:'s)?)?\s*missing\s+health\b",
    flags=re.IGNORECASE,
)
_HEAL_PLACEHOLDER_RE = re.compile(
    r"\bheal(?:ing|s|ed)?\b[^.;]{0,60}?\$(?P<number>\d+)(?!\d)(?:\s*health)?\b",
    flags=re.IGNORECASE,
)
_MODIFIER_MENTION_RE = re.compile(
    r"\bhealing\s+(?:received|done|taken)\b|\bdamage\s+shield\s+strength\b",
    flags=re.IGNORECASE,
)
_AMBIGUOUS_RESTORE_RE = re.compile(
    r"\bcurrent\s+restore\s*:\s*\$(?P<number>\d+)(?!\d)\b",
    flags=re.IGNORECASE,
)


def unresolved_category(fragment: str, coefficient_number: int) -> str:
    text = " ".join(str(fragment or "").split())
    ambiguous = _AMBIGUOUS_RESTORE_RE.search(text)
    if ambiguous is not None and int(ambiguous.group("number")) == int(coefficient_number):
        return "ambiguous_restore_shorthand"
    if _DAMAGE_LINKED_HEAL_RE.search(text):
        return "damage_linked_healing"
    if _MISSING_HEALTH_HEAL_RE.search(text):
        return "missing_health_healing"
    heal_placeholders = {
        int(match.group("number")) for match in _HEAL_PLACEHOLDER_RE.finditer(text)
    }
    if heal_placeholders and int(coefficient_number) not in heal_placeholders:
        return "neighboring_heal_component"
    if _MODIFIER_MENTION_RE.search(text):
        return "modifier_mention"
    return "other"


def load_unresolved_taxonomy(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[UnresolvedHealShieldRow, ...]:
    rows: list[UnresolvedHealShieldRow] = []
    for candidate in load_heal_shield_candidates(database_path, limit=limit):
        if candidate.status != "UNRESOLVED":
            continue
        rows.append(
            UnresolvedHealShieldRow(
                skill_rank_id=candidate.skill_rank_id,
                coefficient_number=candidate.coefficient_number,
                ability_id=candidate.ability_id,
                ability_name=candidate.ability_name,
                category=unresolved_category(candidate.fragment, candidate.coefficient_number),
                candidate_types=candidate.candidate_types,
                resolved_effect_kind=candidate.resolved_effect_kind,
                fragment=candidate.fragment,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[UnresolvedHealShieldRow, ...]) -> Counter[str]:
    return Counter(row.category for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Taxonomize unresolved Phase 6 heal/shield candidates without promoting mechanics."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=60)
    args = parser.parse_args()

    rows = load_unresolved_taxonomy(args.database, limit=args.limit)
    counts = summarize(rows)

    print("\n========================================")
    print(" PHASE 6 UNRESOLVED HEAL / SHIELD TAXONOMY")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Unresolved rows:       {len(rows)}")
    print("\nCATEGORIES")
    for category, count in counts.most_common():
        print(f"  {category:28} {count}")
    print("\nNOTE: categories are evidence triage only; this audit writes no classifications.")

    ordered = sorted(rows, key=lambda row: (row.category, row.skill_rank_id, row.coefficient_number))
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"category={row.category}")
        print(f"candidate_types={','.join(row.candidate_types)}")
        print(f"resolved_effect_kind={row.resolved_effect_kind or '-'}")
        if row.fragment:
            print(f"fragment={' '.join(row.fragment.split())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
