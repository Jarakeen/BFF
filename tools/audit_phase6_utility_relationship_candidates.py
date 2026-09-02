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

from tools.audit_phase6_richer_semantics_taxonomy import load_richer_semantics_taxonomy

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class UtilityCandidateRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    utility_kinds: tuple[str, ...]
    fragment: str


_UTILITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("stun", re.compile(r"\bstun(?:s|ned|ning)?\b", re.IGNORECASE)),
    ("immobilize", re.compile(r"\bimmobiliz(?:e|es|ed|ing)\b", re.IGNORECASE)),
    (
        "movement_speed_reduction",
        re.compile(
            r"\b(?:reducing|reduces?|reduced)\b[^.;]{0,70}?\bmovement\s+speed\b|"
            r"\bmovement\s+speed\b[^.;]{0,70}?\b(?:reduced|slowed?)\b",
            re.IGNORECASE,
        ),
    ),
    ("interrupt_immunity", re.compile(r"\binterrupt\s+immunity\b", re.IGNORECASE)),
    ("knockback", re.compile(r"\bknock(?:back|ed\s+back|s?\s+back)\b", re.IGNORECASE)),
    ("pull", re.compile(r"\bpull(?:s|ed|ing)?\b", re.IGNORECASE)),
    ("taunt", re.compile(r"\btaunt(?:s|ed|ing)?\b", re.IGNORECASE)),
)


def utility_kinds(fragment: str) -> tuple[str, ...]:
    text = " ".join(str(fragment or "").split())
    return tuple(name for name, pattern in _UTILITY_PATTERNS if pattern.search(text))


def load_utility_candidates(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[UtilityCandidateRow, ...]:
    rows: list[UtilityCandidateRow] = []
    for item in load_richer_semantics_taxonomy(database_path, limit=limit):
        if item.category != "utility_relationship_candidate":
            continue
        rows.append(
            UtilityCandidateRow(
                skill_rank_id=item.skill_rank_id,
                coefficient_number=item.coefficient_number,
                ability_id=item.ability_id,
                ability_name=item.ability_name,
                utility_kinds=utility_kinds(item.fragment),
                fragment=item.fragment,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[UtilityCandidateRow, ...]) -> dict[str, object]:
    kinds = Counter(kind for row in rows for kind in row.utility_kinds)
    unresolved = sum(not row.utility_kinds for row in rows)
    multi_kind = sum(len(row.utility_kinds) > 1 for row in rows)
    return {
        "rows": len(rows),
        "kinds": kinds,
        "unresolved": unresolved,
        "multi_kind": multi_kind,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit still-uncovered Phase 6 utility relationship candidates. "
            "This is taxonomy only and never promotes utility mechanics."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=80)
    args = parser.parse_args()

    rows = load_utility_candidates(args.database, limit=args.limit)
    summary = summarize(rows)
    kinds: Counter[str] = summary["kinds"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 UTILITY RELATIONSHIP CANDIDATES")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {summary['rows']}")
    print(f"Unresolved taxonomy:   {summary['unresolved']}")
    print(f"Multi-kind rows:       {summary['multi_kind']}")

    print("\nUTILITY KINDS")
    for name, count in kinds.most_common():
        print(f"  {name:28} {count}")

    print("\nNOTE: taxonomy only; durations, triggers, immunity state, and uptime remain later concerns.")

    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"utility_kinds={','.join(row.utility_kinds) if row.utility_kinds else '-'}")
        if row.fragment:
            print(f"fragment={' '.join(row.fragment.split())}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
