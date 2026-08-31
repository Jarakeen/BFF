from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_text_evidence import extract_component_text_evidence
from minmax.skill_critical_observation import CriticalComponentCandidate, CriticalEventFamily
from tools.audit_skill_coefficient_slots import load_slot_audit
from tools.audit_skill_component_text_semantics import is_active_coefficient


DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class CriticalMappingGroup:
    ability_id: int
    event_family: CriticalEventFamily
    candidates: tuple[CriticalComponentCandidate, ...]

    @property
    def is_unique(self) -> bool:
        return len(self.candidates) == 1


@dataclass(frozen=True)
class CriticalMappingSummary:
    active_coefficients: int
    crit_relevant_components: int
    groups: int
    unique_groups: int
    ambiguous_groups: int
    unique_components: int
    ambiguous_components: int


def load_critical_mapping_groups(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[tuple[CriticalMappingGroup, ...], CriticalMappingSummary]:
    rows = load_slot_audit(database_path, limit=limit)
    active = 0
    grouped: dict[tuple[int, CriticalEventFamily], list[CriticalComponentCandidate]] = defaultdict(list)

    for row in rows:
        if not is_active_coefficient(row):
            continue
        active += 1
        if row.raw_slot_matches_coefficient is not True:
            continue

        evidence = extract_component_text_evidence(row.coef_description, row.coefficient_number)
        if evidence.effect_kind not in {"damage", "heal"} or evidence.is_dot is None:
            continue

        candidate = CriticalComponentCandidate(
            skill_rank_id=int(row.skill_rank_id),
            coefficient_number=int(row.coefficient_number),
            ability_id=int(row.ability_id),
            effect_kind=SkillEffectKind(evidence.effect_kind),
            is_dot=bool(evidence.is_dot),
            can_crit=None,
        )
        family = candidate.event_family
        if family is not None:
            grouped[(candidate.ability_id, family)].append(candidate)

    groups = tuple(
        CriticalMappingGroup(
            ability_id=ability_id,
            event_family=event_family,
            candidates=tuple(candidates),
        )
        for (ability_id, event_family), candidates in sorted(
            grouped.items(), key=lambda item: (item[0][0], item[0][1].value)
        )
    )

    unique = tuple(group for group in groups if group.is_unique)
    ambiguous = tuple(group for group in groups if not group.is_unique)
    summary = CriticalMappingSummary(
        active_coefficients=active,
        crit_relevant_components=sum(len(group.candidates) for group in groups),
        groups=len(groups),
        unique_groups=len(unique),
        ambiguous_groups=len(ambiguous),
        unique_components=sum(len(group.candidates) for group in unique),
        ambiguous_components=sum(len(group.candidates) for group in ambiguous),
    )
    return groups, summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit whether runtime critical observations can map uniquely from "
            "abilityId + damage/heal + direct/periodic to one coefficient. Read-only."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=30)
    args = parser.parse_args()

    groups, summary = load_critical_mapping_groups(args.database, limit=args.limit)
    ambiguous = [group for group in groups if not group.is_unique]

    print("\n========================================")
    print(" PHASE 3 CRITICAL MAPPING AUDIT")
    print("========================================")
    print(f"Database:                 {args.database}")
    print(f"Active coefficients:      {summary.active_coefficients}")
    print(f"Crit-relevant components: {summary.crit_relevant_components}")
    print(f"Ability/event groups:     {summary.groups}")
    print(f"Unique groups:            {summary.unique_groups}")
    print(f"Ambiguous groups:         {summary.ambiguous_groups}")
    print(f"Unique components:        {summary.unique_components}")
    print(f"Ambiguous components:     {summary.ambiguous_components}")
    print("\nNOTE: uniqueness does not prove can_crit; it only proves that a future")
    print("positive runtime critical observation could be assigned without guessing.")
    print("Absence of a critical observation never proves can_crit=False.")

    for group in ambiguous[: max(0, args.samples)]:
        keys = ", ".join(
            f"rank={candidate.skill_rank_id}/coef={candidate.coefficient_number}"
            for candidate in group.candidates
        )
        print("\n----------------------------------------")
        print(
            f"ability={group.ability_id} family={group.event_family.value} "
            f"components={len(group.candidates)}"
        )
        print(keys)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
