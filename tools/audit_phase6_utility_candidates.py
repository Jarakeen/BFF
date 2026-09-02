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
from tools.audit_phase6_component_gaps import load_phase6_gap_matrix
from tools.audit_phase6_richer_semantics_taxonomy import richer_category

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class UtilityCandidateRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    utility_types: tuple[str, ...]
    fragment: str


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("stun", re.compile(r"\bstun(?:s|ned|ning)?\b", re.IGNORECASE)),
    ("immobilize", re.compile(r"\bimmobiliz(?:e|es|ed|ing)\b", re.IGNORECASE)),
    ("movement_speed", re.compile(r"\bmovement\s+speed\b", re.IGNORECASE)),
    (
        "knockback",
        re.compile(
            r"\b(?:knockback|knock(?:s|ed|ing)?\s+(?:\w+\s+){0,2}?back)\b",
            re.IGNORECASE,
        ),
    ),
    ("pull", re.compile(r"\bpull(?:s|ed|ing)?\b", re.IGNORECASE)),
    ("taunt", re.compile(r"\btaunt(?:s|ed|ing)?\b", re.IGNORECASE)),
    ("interrupt_immunity", re.compile(r"\binterrupt\s+immunity\b", re.IGNORECASE)),
)


def utility_types(fragment: str) -> tuple[str, ...]:
    text = " ".join(str(fragment or "").split())
    return tuple(label for label, pattern in _PATTERNS if pattern.search(text))


def load_utility_candidates(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[UtilityCandidateRow, ...]:
    """Return the stable original Phase 6 utility-candidate corpus.

    This audit intentionally starts from the original gap matrix rather than the
    remaining-semantics reconciliation. Canonical promotions must not make the
    audit forget rows it already proved, otherwise coverage appears to shrink as
    the implementation improves.
    """

    rows: list[UtilityCandidateRow] = []
    for gap in load_phase6_gap_matrix(database_path, limit=limit):
        if gap.disposition != "richer_component_semantics":
            continue
        evidence = extract_component_text_evidence(gap.fragment, gap.coefficient_number)
        category = richer_category(gap.fragment, gap.coefficient_number, evidence.effect_kind)
        if category != "utility_relationship_candidate":
            continue
        kinds = utility_types(gap.fragment)
        rows.append(
            UtilityCandidateRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                ability_name=gap.name,
                utility_types=kinds,
                fragment=gap.fragment,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[UtilityCandidateRow, ...]) -> Counter[str]:
    return Counter(kind for row in rows for kind in row.utility_types)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit coefficient-local Phase 6 utility relationship candidates without writing mechanics."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=80)
    args = parser.parse_args()

    rows = load_utility_candidates(args.database, limit=args.limit)
    counts = summarize(rows)

    print("\n========================================")
    print(" PHASE 6 UTILITY COMPONENT CANDIDATES")
    print("========================================")
    print(f"Database: {args.database}")
    print(f"Rows:     {len(rows)}")
    print("\nUTILITY TYPES")
    for kind, count in counts.most_common():
        print(f"  {kind:24} {count}")
    print("\nNOTE: audit only; no utility mechanics are written.")

    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"utility_types={','.join(row.utility_types) or '-'}")
        print(f"fragment={' '.join(row.fragment.split())}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
