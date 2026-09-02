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
class RicherSemanticsTaxonomyRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    category: str
    effect_kind: str | None
    signals: tuple[str, ...]
    fragment: str


_STORED_DAMAGE_SCALING_RE = re.compile(
    r"\bincreases?\s+based\s+on\s+the\s+amount\s+of\s+damage\b",
    re.IGNORECASE,
)
_PER_TICK_RAMP_RE = re.compile(
    r"\bincreases?\s+by\s+\d+(?:\.\d+)?\s*%\s+per\s+tick\b",
    re.IGNORECASE,
)
_DIRECT_HEAL_RE = re.compile(
    r"\bheal(?:s|ed|ing)?\b[^.;]{0,80}?\$(?P<number>\d+)(?!\d)(?:\s+health)?\b",
    re.IGNORECASE,
)
_MULTI_DAMAGE_RE = re.compile(
    r"\$(?:\d+)(?!\d)[^.;]{0,100}?\bdamage\b[^.;]{0,120}?\$(?:\d+)(?!\d)[^.;]{0,100}?\bdamage\b",
    re.IGNORECASE,
)
_UTILITY_RE = re.compile(
    r"\b(?:stun(?:s|ned|ning)?|immobiliz(?:e|es|ed|ing)|movement\s+speed|interrupt\s+immunity|knock(?:back|ed)?|pull(?:s|ed|ing)?|taunt(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)


def richer_category(fragment: str, coefficient_number: int, effect_kind: str | None) -> str:
    text = " ".join(str(fragment or "").split())
    if _STORED_DAMAGE_SCALING_RE.search(text):
        return "stored_damage_scaling"
    if _PER_TICK_RAMP_RE.search(text):
        return "per_tick_damage_ramp"

    direct_heals = {
        int(match.group("number"))
        for match in _DIRECT_HEAL_RE.finditer(text)
    }
    if int(coefficient_number) in direct_heals and effect_kind == "heal":
        return "direct_heal_classification_gap"

    if effect_kind == "damage" and _MULTI_DAMAGE_RE.search(text):
        return "multi_damage_classification_gap"

    if _UTILITY_RE.search(text):
        return "utility_relationship_candidate"

    lower = text.casefold()
    if any(token in lower for token in (" if ", " while ", " when ", " whenever ", " after ", " upon ")):
        return "conditional_or_temporal_candidate"

    return "other_richer_semantics"


def load_richer_semantics_taxonomy(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[RicherSemanticsTaxonomyRow, ...]:
    rows: list[RicherSemanticsTaxonomyRow] = []
    for item in load_remaining_phase6_semantics(database_path, limit=limit):
        if item.is_covered or item.gap.disposition != "richer_component_semantics":
            continue
        gap = item.gap
        evidence = extract_component_text_evidence(gap.fragment, gap.coefficient_number)
        rows.append(
            RicherSemanticsTaxonomyRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                ability_name=gap.name,
                category=richer_category(gap.fragment, gap.coefficient_number, evidence.effect_kind),
                effect_kind=evidence.effect_kind,
                signals=gap.signals,
                fragment=gap.fragment,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[RicherSemanticsTaxonomyRow, ...]) -> Counter[str]:
    return Counter(row.category for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Taxonomize still-uncovered Phase 6 richer component semantics without promoting mechanics."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=80)
    args = parser.parse_args()

    rows = load_richer_semantics_taxonomy(args.database, limit=args.limit)
    counts = summarize(rows)

    print("\n========================================")
    print(" PHASE 6 RICHER SEMANTICS TAXONOMY")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Rows:                  {len(rows)}")
    print("\nCATEGORIES")
    for category, count in counts.most_common():
        print(f"  {category:32} {count}")
    print("\nNOTE: taxonomy only; no mechanics or classifications are written.")

    ordered = sorted(rows, key=lambda row: (row.category, row.skill_rank_id, row.coefficient_number))
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"category={row.category}")
        print(f"effect_kind={row.effect_kind or '-'}")
        if row.signals:
            print(f"signals={','.join(row.signals)}")
        if row.fragment:
            print(f"fragment={' '.join(row.fragment.split())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
