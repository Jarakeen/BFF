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

from minmax.skill_component_utility_effect_repository import SkillComponentUtilityEffectRepository
from tools.audit_phase6_utility_candidates import load_utility_candidates

DEFAULT_DATABASE = ROOT / "data" / "eso.db"
_CONTEXT_ONLY_UTILITY_RE = re.compile(
    r"\bif\s+the\s+stun\b|\bafter\s+the\s+stun\s+ends?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UtilityAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    promoted_types: tuple[str, ...]
    fragment: str
    neighboring_owner: int | None = None
    neighboring_types: tuple[str, ...] = ()
    context_only: bool = False

    @property
    def promoted(self) -> bool:
        return bool(self.promoted_types)

    @property
    def neighbor_owned(self) -> bool:
        return self.neighboring_owner is not None and bool(self.neighboring_types)

    @property
    def accounted_for(self) -> bool:
        return self.promoted or self.neighbor_owned or self.context_only


def _neighboring_utility_owner(
    repository: SkillComponentUtilityEffectRepository,
    skill_rank_id: int,
    coefficient_number: int,
) -> tuple[int | None, tuple[str, ...]]:
    """Find an explicit utility effect on a sibling coefficient, if one owns it."""

    for sibling in range(1, 7):
        if sibling == int(coefficient_number):
            continue
        effects = repository.resolve(skill_rank_id, sibling)
        if effects:
            return sibling, tuple(effect.effect_type.value for effect in effects)
    return None, ()


def _is_context_only_utility(fragment: str) -> bool:
    """Return True when utility wording is explicitly prior-state/condition text."""

    return _CONTEXT_ONLY_UTILITY_RE.search(" ".join(str(fragment or "").split())) is not None


def load_utility_audit(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[UtilityAuditRow, ...]:
    path = Path(database_path)
    repository = SkillComponentUtilityEffectRepository(path)
    rows: list[UtilityAuditRow] = []
    for candidate in load_utility_candidates(path, limit=limit):
        effects = repository.resolve(candidate.skill_rank_id, candidate.coefficient_number)
        neighboring_owner: int | None = None
        neighboring_types: tuple[str, ...] = ()
        context_only = False
        if not effects:
            context_only = _is_context_only_utility(candidate.fragment)
        if not effects and not context_only:
            neighboring_owner, neighboring_types = _neighboring_utility_owner(
                repository,
                candidate.skill_rank_id,
                candidate.coefficient_number,
            )
        rows.append(
            UtilityAuditRow(
                skill_rank_id=candidate.skill_rank_id,
                coefficient_number=candidate.coefficient_number,
                ability_id=candidate.ability_id,
                ability_name=candidate.ability_name,
                promoted_types=tuple(effect.effect_type.value for effect in effects),
                fragment=candidate.fragment,
                neighboring_owner=neighboring_owner,
                neighboring_types=neighboring_types,
                context_only=context_only,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[UtilityAuditRow, ...]) -> dict[str, object]:
    promoted = [row for row in rows if row.promoted]
    context_only = [row for row in rows if row.context_only]
    neighbor_owned = [row for row in rows if row.neighbor_owned]
    unresolved = [row for row in rows if not row.accounted_for]
    return {
        "candidates": len(rows),
        "promoted": len(promoted),
        "context_only": len(context_only),
        "neighbor_owned": len(neighbor_owned),
        "unresolved": len(unresolved),
        "types": Counter(kind for row in promoted for kind in row.promoted_types),
        "neighbor_types": Counter(kind for row in neighbor_owned for kind in row.neighboring_types),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit explicit Phase 6 component utility effects against the real coefficient corpus."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=80)
    args = parser.parse_args()

    rows = load_utility_audit(args.database, limit=args.limit)
    summary = summarize(rows)
    types: Counter[str] = summary["types"]  # type: ignore[assignment]
    neighbor_types: Counter[str] = summary["neighbor_types"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 COMPONENT UTILITY EFFECTS")
    print("========================================")
    print(f"Database:               {args.database}")
    print(f"Candidates:             {summary['candidates']}")
    print(f"Canonically promoted:   {summary['promoted']}")
    print(f"Context-only signals:   {summary['context_only']}")
    print(f"Neighbor-owned signals: {summary['neighbor_owned']}")
    print(f"Still unresolved:       {summary['unresolved']}")

    print("\nUTILITY TYPES")
    for kind, count in types.most_common():
        print(f"  {kind:28} {count}")
    if neighbor_types:
        print("\nNEIGHBOR-OWNED UTILITY TYPES")
        for kind, count in neighbor_types.most_common():
            print(f"  {kind:28} {count}")
    print("\nNOTE: duration, cadence, triggers, and current combat state remain outside this Phase 6 primitive.")

    ordered = sorted(
        rows,
        key=lambda row: (
            0 if row.promoted else 1 if row.context_only else 2 if row.neighbor_owned else 3,
            row.skill_rank_id,
            row.coefficient_number,
        ),
    )
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        if row.promoted:
            print("status=PROMOTED")
            print(f"utility_types={','.join(row.promoted_types)}")
        elif row.context_only:
            print("status=CONTEXT_ONLY")
            print("utility_types=-")
        elif row.neighbor_owned:
            print("status=NEIGHBOR_OWNED")
            print("utility_types=-")
            print(f"neighbor_owner=coef{row.neighboring_owner}")
            print(f"neighbor_utility_types={','.join(row.neighboring_types)}")
        else:
            print("status=UNRESOLVED")
            print("utility_types=-")
        print(f"fragment={' '.join(row.fragment.split())}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
