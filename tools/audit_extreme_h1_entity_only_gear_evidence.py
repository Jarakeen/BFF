from __future__ import annotations

"""Review extracted ESO-Hub entity-only gear evidence before any DB normalization.

This is intentionally read-only. It validates the 60-row source corpus, groups
set types, checks perfected/non-perfected pairing, reviews bonus-count patterns,
and flags rows that should not be auto-normalized yet.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "research" / "raw" / "eso_hub_entity_only_gear_sets.json"


def _base_name(name: str) -> str:
    value = str(name or "").strip()
    prefix = "Perfected "
    return value[len(prefix):] if value.startswith(prefix) else value


def build_review(rows: list[dict]) -> dict:
    by_type = Counter(str(row.get("type") or "").strip() or "<blank>" for row in rows)
    bonus_counts = Counter(len(row.get("bonuses") or ()) for row in rows)
    modified_skill_counts = Counter(len(row.get("modified_skills") or ()) for row in rows)

    names = {str(row.get("name") or "").strip() for row in rows}
    base_groups: dict[str, list[str]] = defaultdict(list)
    for name in sorted(names, key=str.casefold):
        base_groups[_base_name(name)].append(name)

    unpaired: list[tuple[str, tuple[str, ...]]] = []
    for base, group in sorted(base_groups.items(), key=lambda item: item[0].casefold()):
        expected = {base, f"Perfected {base}"}
        actual = set(group)
        if actual != expected:
            unpaired.append((base, tuple(sorted(actual, key=str.casefold))))

    unresolved = [
        str(row.get("name") or "")
        for row in rows
        if row.get("unresolved")
    ]
    no_bonus = [
        str(row.get("name") or "")
        for row in rows
        if not row.get("bonuses")
    ]
    no_modified_skills = [
        str(row.get("name") or "")
        for row in rows
        if not row.get("modified_skills")
    ]
    non_arena = [
        (
            str(row.get("name") or ""),
            str(row.get("type") or ""),
            str(row.get("location") or ""),
            tuple(row.get("bonuses") or ()),
        )
        for row in rows
        if str(row.get("type") or "").strip().casefold() != "arena"
    ]

    perfected_pairs = sum(
        1
        for base, group in base_groups.items()
        if set(group) == {base, f"Perfected {base}"}
    )

    return {
        "row_count": len(rows),
        "type_counts": dict(sorted(by_type.items(), key=lambda item: item[0].casefold())),
        "bonus_count_histogram": dict(sorted(bonus_counts.items())),
        "modified_skill_count_histogram": dict(sorted(modified_skill_counts.items())),
        "perfected_pair_count": perfected_pairs,
        "unpaired": unpaired,
        "unresolved": unresolved,
        "no_bonus": no_bonus,
        "no_modified_skills": no_modified_skills,
        "non_arena": non_arena,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review extracted entity-only ESO-Hub gear evidence"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()

    rows = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("Expected a JSON list")

    review = build_review(rows)

    print("EXTREME H1 ENTITY-ONLY GEAR EVIDENCE REVIEW")
    print(f"input={args.input}")
    print(f"row_count={review['row_count']}")
    print(f"type_counts={review['type_counts']}")
    print(f"bonus_count_histogram={review['bonus_count_histogram']}")
    print(
        "modified_skill_count_histogram="
        f"{review['modified_skill_count_histogram']}"
    )
    print(f"perfected_pair_count={review['perfected_pair_count']}")
    print(f"unpaired_count={len(review['unpaired'])}")
    print(f"unresolved_count={len(review['unresolved'])}")
    print(f"no_bonus_count={len(review['no_bonus'])}")
    print(f"no_modified_skills_count={len(review['no_modified_skills'])}")
    print(f"non_arena_count={len(review['non_arena'])}")

    if review["unpaired"]:
        print()
        print("[UNPAIRED]")
        for base, names in review["unpaired"]:
            print(f"{base!r}: {names}")

    if review["non_arena"]:
        print()
        print("[NON_ARENA]")
        for name, set_type, location, bonuses in review["non_arena"]:
            print(f"name={name!r} type={set_type!r} location={location!r}")
            for bonus in bonuses:
                print(f"  bonus={bonus}")

    if review["no_modified_skills"]:
        print()
        print("[NO_MODIFIED_SKILLS]")
        for name in review["no_modified_skills"]:
            print(name)

    print()
    print(
        "NEXT_STEP=normalize only rows whose source type/bonus/skill-line shape "
        "is proven; keep non-Arena or structurally ambiguous rows fail-closed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
