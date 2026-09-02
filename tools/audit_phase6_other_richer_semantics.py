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

from tools.audit_phase6_richer_semantics_taxonomy import (
    RicherSemanticsTaxonomyRow,
    load_richer_semantics_taxonomy,
)

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class OtherRicherSemanticsRow:
    source: RicherSemanticsTaxonomyRow
    category: str


_PERIODIC_DAMAGE_RE = re.compile(
    r"\b(?:damage\s+every\s+\d|damage\s+over\s+\d|every\s+\d+(?:\.\d+)?\s+seconds?[^.;]{0,80}\bdamage\b)",
    re.IGNORECASE,
)
_DIRECT_DAMAGE_RE = re.compile(
    r"\b(?:deal(?:s|ing)?|take(?:s|ing)?)\b[^.;]{0,100}?\$\d+(?!\d)[^.;]{0,50}?\bdamage\b",
    re.IGNORECASE,
)
_SCALING_OR_MODIFIER_RE = re.compile(
    r"\b(?:increase(?:s|d|ing)?|decrease(?:s|d|ing)?|reduce(?:s|d|ing)?|more\s+damage|less\s+damage|based\s+on|scal(?:e|es|ed|ing)\s+(?:off|with|based))\b",
    re.IGNORECASE,
)
_SECONDARY_WORDING_RE = re.compile(
    r"\b(?:also|additional(?:ly)?|then)\b",
    re.IGNORECASE,
)
_DURATION_OR_CADENCE_RE = re.compile(
    r"\b(?:for|over)\s+\d+(?:\.\d+)?\s+seconds?\b|\bevery\s+\d+(?:\.\d+)?\s+seconds?\b",
    re.IGNORECASE,
)
_EFFECT_WORDING_RE = re.compile(
    r"\b(?:major|minor)\s+[A-Z][A-Za-z' -]+\b|\b(?:burning|chilled|concussion|diseased|hemorrhaging|poisoned|sundered|off-balance)\b",
)


def detail_category(row: RicherSemanticsTaxonomyRow) -> str:
    text = " ".join(str(row.fragment or "").split())

    if row.effect_kind == "damage" and _PERIODIC_DAMAGE_RE.search(text):
        return "periodic_damage_classification_gap"
    if row.effect_kind == "damage" and _DIRECT_DAMAGE_RE.search(text):
        if _SCALING_OR_MODIFIER_RE.search(text):
            return "damage_scaling_or_modifier_candidate"
        if _SECONDARY_WORDING_RE.search(text):
            return "secondary_damage_classification_gap"
        if _DURATION_OR_CADENCE_RE.search(text):
            return "damage_with_duration_or_cadence"
        return "direct_damage_classification_gap"
    if _SCALING_OR_MODIFIER_RE.search(text):
        return "scaling_or_modifier_candidate"
    if _EFFECT_WORDING_RE.search(text):
        return "named_or_status_effect_wording"
    if _SECONDARY_WORDING_RE.search(text):
        return "secondary_wording_candidate"
    if _DURATION_OR_CADENCE_RE.search(text):
        return "duration_or_cadence_candidate"
    if row.signals:
        return "signal_only_candidate"
    return "uncategorized_other"


def load_other_richer_semantics(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[OtherRicherSemanticsRow, ...]:
    rows: list[OtherRicherSemanticsRow] = []
    for row in load_richer_semantics_taxonomy(database_path, limit=limit):
        if row.category != "other_richer_semantics":
            continue
        rows.append(OtherRicherSemanticsRow(source=row, category=detail_category(row)))
    return tuple(rows)


def summarize(rows: tuple[OtherRicherSemanticsRow, ...]) -> Counter[str]:
    return Counter(row.category for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Second-pass taxonomy for Phase 6 other richer semantics; read-only and non-promoting."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=100)
    args = parser.parse_args()

    rows = load_other_richer_semantics(args.database, limit=args.limit)
    counts = summarize(rows)

    print("\n========================================")
    print(" PHASE 6 OTHER RICHER SEMANTICS")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Rows:                  {len(rows)}")
    print("\nCATEGORIES")
    for category, count in counts.most_common():
        print(f"  {category:36} {count}")
    print("\nNOTE: second-pass taxonomy only; no mechanics or classifications are written.")

    ordered = sorted(
        rows,
        key=lambda item: (item.category, item.source.skill_rank_id, item.source.coefficient_number),
    )
    for item in ordered[: max(0, args.samples)]:
        row = item.source
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"category={item.category}")
        print(f"effect_kind={row.effect_kind or '-'}")
        if row.signals:
            print(f"signals={','.join(row.signals)}")
        if row.fragment:
            print(f"fragment={' '.join(row.fragment.split())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
