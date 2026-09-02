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

from tools.audit_phase6_other_richer_semantics import load_other_richer_semantics

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class SignalOnlySemanticsRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    category: str
    effect_kind: str | None
    fragment: str


_ATTACK_TRIGGERED_HEAL_RE = re.compile(
    r"\b(?:light|heavy)\s+attacks?\b[^.;]{0,120}?\b(?:restore|heal)\b[^.;]{0,80}?\$\d+(?!\d)",
    re.IGNORECASE,
)
_MULTI_HEAL_RE = re.compile(
    r"\bheal(?:s|ed|ing)?\b[^.;]{0,140}?\$\d+(?!\d)[^.;]{0,140}?\$\d+(?!\d)",
    re.IGNORECASE,
)


def signal_only_category(fragment: str, effect_kind: str | None) -> str:
    text = " ".join(str(fragment or "").split())
    if effect_kind == "heal" and _ATTACK_TRIGGERED_HEAL_RE.search(text):
        return "phase7_attack_triggered_heal"
    if effect_kind == "heal" and _MULTI_HEAL_RE.search(text):
        return "multi_heal_classification_gap"
    return "unresolved_signal_only"


def load_signal_only_semantics(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[SignalOnlySemanticsRow, ...]:
    rows: list[SignalOnlySemanticsRow] = []
    for item in load_other_richer_semantics(database_path, limit=limit):
        if item.category != "signal_only_candidate":
            continue
        source = item.source
        rows.append(
            SignalOnlySemanticsRow(
                skill_rank_id=source.skill_rank_id,
                coefficient_number=source.coefficient_number,
                ability_id=source.ability_id,
                ability_name=source.ability_name,
                category=signal_only_category(source.fragment, source.effect_kind),
                effect_kind=source.effect_kind,
                fragment=source.fragment,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[SignalOnlySemanticsRow, ...]) -> Counter[str]:
    return Counter(row.category for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split Phase 6 signal-only richer rows into classification leftovers and later-phase trigger semantics."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=80)
    args = parser.parse_args()

    rows = load_signal_only_semantics(args.database, limit=args.limit)
    counts = summarize(rows)

    print("\n========================================")
    print(" PHASE 6 SIGNAL-ONLY SEMANTICS")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Rows:                  {len(rows)}")
    print("\nCATEGORIES")
    for category, count in counts.most_common():
        print(f"  {category:32} {count}")
    print("\nNOTE: audit only; Phase 7 trigger rows are intentionally not promoted as Phase 6 mechanics.")

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
