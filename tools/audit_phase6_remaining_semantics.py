from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_condition_repository import SkillComponentConditionRepository
from minmax.skill_component_conditional_consequence_repository import (
    SkillComponentConditionalConsequenceRepository,
)
from minmax.skill_component_damage_scaling_repository import (
    SkillComponentDamageScalingRepository,
)
from minmax.skill_component_effect_relationship_repository import (
    SkillComponentEffectRelationshipRepository,
)
from minmax.skill_component_missing_health_healing_repository import (
    SkillComponentMissingHealthHealingRepository,
)
from minmax.skill_component_resource_event_repository import (
    SkillComponentResourceEventRepository,
)
from minmax.skill_component_role_repository import SkillComponentRoleRepository
from minmax.skill_component_secondary_healing_repository import (
    SkillComponentSecondaryHealingRepository,
)
from minmax.skill_component_stat_scaling_repository import SkillComponentStatScalingRepository
from minmax.skill_component_trigger_relationship_repository import (
    SkillComponentTriggerRelationshipRepository,
)
from minmax.skill_component_utility_effect_repository import (
    SkillComponentUtilityEffectRepository,
)
from tools.audit_phase6_component_gaps import Phase6GapRow, load_phase6_gap_matrix

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class RemainingPhase6Row:
    gap: Phase6GapRow
    covered_by: tuple[str, ...]

    @property
    def is_covered(self) -> bool:
        return bool(self.covered_by)


def _coverage_for_row(
    row: Phase6GapRow,
    *,
    effects: SkillComponentEffectRelationshipRepository,
    conditions: SkillComponentConditionRepository,
    consequences: SkillComponentConditionalConsequenceRepository,
    damage_scaling: SkillComponentDamageScalingRepository,
    resources: SkillComponentResourceEventRepository,
    roles: SkillComponentRoleRepository,
    secondary_healing: SkillComponentSecondaryHealingRepository,
    missing_health_healing: SkillComponentMissingHealthHealingRepository,
    stat_scaling: SkillComponentStatScalingRepository,
    triggers: SkillComponentTriggerRelationshipRepository,
    utility_effects: SkillComponentUtilityEffectRepository,
) -> tuple[str, ...]:
    rank = row.skill_rank_id
    coef = row.coefficient_number
    covered: list[str] = []

    if effects.resolve(rank, coef):
        covered.append("named_effect_application")
    if consequences.resolve(rank, coef):
        covered.append("conditional_consequence")
    elif conditions.resolve(rank, coef):
        covered.append("component_condition")
    if damage_scaling.resolve(rank, coef):
        covered.append("damage_scaling")
    if resources.resolve(rank, coef):
        covered.append("resource_event")
    if roles.resolve(rank, coef):
        covered.append("component_role")
    if secondary_healing.resolve(rank, coef):
        covered.append("damage_linked_healing")
    if missing_health_healing.resolve(rank, coef):
        covered.append("missing_health_healing")
    if stat_scaling.resolve(rank, coef):
        covered.append("stat_scaling")
    if triggers.resolve(rank, coef):
        covered.append("component_trigger")
    if utility_effects.resolve(rank, coef):
        covered.append("utility_effect")

    return tuple(covered)


def load_remaining_phase6_semantics(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[RemainingPhase6Row, ...]:
    path = Path(database_path)
    repositories = {
        "effects": SkillComponentEffectRelationshipRepository(path),
        "conditions": SkillComponentConditionRepository(path),
        "consequences": SkillComponentConditionalConsequenceRepository(path),
        "damage_scaling": SkillComponentDamageScalingRepository(path),
        "resources": SkillComponentResourceEventRepository(path),
        "roles": SkillComponentRoleRepository(path),
        "secondary_healing": SkillComponentSecondaryHealingRepository(path),
        "missing_health_healing": SkillComponentMissingHealthHealingRepository(path),
        "stat_scaling": SkillComponentStatScalingRepository(path),
        "triggers": SkillComponentTriggerRelationshipRepository(path),
        "utility_effects": SkillComponentUtilityEffectRepository(path),
    }

    rows: list[RemainingPhase6Row] = []
    for gap in load_phase6_gap_matrix(path, limit=limit):
        rows.append(
            RemainingPhase6Row(
                gap=gap,
                covered_by=_coverage_for_row(gap, **repositories),
            )
        )
    return tuple(rows)


def summarize(rows: tuple[RemainingPhase6Row, ...]) -> dict[str, object]:
    covered = [row for row in rows if row.is_covered]
    remaining = [row for row in rows if not row.is_covered]
    return {
        "rows": len(rows),
        "covered": len(covered),
        "remaining": len(remaining),
        "coverage": Counter(label for row in covered for label in row.covered_by),
        "dispositions": Counter(row.gap.disposition for row in remaining),
        "signals": Counter(signal for row in remaining for signal in row.gap.signals),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile the original Phase 6 gap matrix against canonical Phase 6 "
            "repositories and report only semantics that still lack a Phase 6 model."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=60)
    args = parser.parse_args()

    rows = load_remaining_phase6_semantics(args.database, limit=args.limit)
    summary = summarize(rows)
    coverage: Counter[str] = summary["coverage"]  # type: ignore[assignment]
    dispositions: Counter[str] = summary["dispositions"]  # type: ignore[assignment]
    signals: Counter[str] = summary["signals"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 REMAINING COMPONENT SEMANTICS")
    print("========================================")
    print(f"Database:                 {args.database}")
    print(f"Original gap rows:        {summary['rows']}")
    print(f"Covered by Phase 6:       {summary['covered']}")
    print(f"Still needing semantics:  {summary['remaining']}")

    print("\nCANONICAL PHASE 6 COVERAGE")
    for name, count in coverage.most_common():
        print(f"  {name:28} {count}")

    print("\nREMAINING DISPOSITION")
    for name, count in dispositions.most_common():
        print(f"  {name:28} {count}")

    print("\nREMAINING SIGNALS")
    for name, count in signals.most_common():
        print(f"  {name:28} {count}")

    print(
        "\nNOTE: this is a reconciliation audit only. It does not write classifications "
        "or evaluate Phase 7 timing/state."
    )

    remaining_rows = [row for row in rows if not row.is_covered]
    for item in remaining_rows[: max(0, args.samples)]:
        row = item.gap
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.name}"
        )
        print(f"phase3_gap={','.join(row.phase3_reasons)}")
        print(f"disposition={row.disposition}")
        if row.signals:
            print(f"signals={','.join(row.signals)}")
        if row.linked_effects:
            print(f"linked_effects={', '.join(row.linked_effects)}")
        if row.named_combat_effects:
            print(f"named_combat_effects={', '.join(row.named_combat_effects)}")
        if row.fragment:
            print(f"fragment={' '.join(row.fragment.split())}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
