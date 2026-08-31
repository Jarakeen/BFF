from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from minmax.combat_state import CombatState
from minmax.dd_mitigation import calculate_dd_mitigation
from minmax.dd_stat_evaluation import DDStatEvaluation
from minmax.skill_coefficient import SkillCoefficient, evaluate_skill_coefficient
from minmax.skill_combat_damage import calculate_classified_skill_combat_damage
from minmax.skill_component_repository import SkillComponentRepository
from minmax.skill_damage import SkillDamageResult


def _select_real_component(database_path: Path) -> sqlite3.Row | None:
    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        return db.execute(
            """
            SELECT
                c.skill_rank_id,
                c.coefficient_number,
                c.damage_type,
                c.is_dot,
                c.is_aoe,
                c.can_crit,
                c.source,
                sc.type,
                sc.a,
                sc.b,
                sc.c,
                sc.r,
                sc.avg,
                sr.ability_id,
                COALESCE(a.name, sr.raw_name, '') AS skill_name
            FROM skill_component_classification c
            JOIN skill_coefficient sc
              ON sc.skill_rank_id = c.skill_rank_id
             AND sc.coefficient_number = c.coefficient_number
            LEFT JOIN skill_rank sr
              ON sr.id = c.skill_rank_id
            LEFT JOIN ability a
              ON a.ability_id = sr.ability_id
            WHERE c.effect_kind = 'damage'
              AND c.damage_type IS NOT NULL
              AND c.is_dot IS NOT NULL
              AND c.is_aoe IS NOT NULL
              AND c.can_crit = 1
              AND sc.type = '8'
            ORDER BY c.skill_rank_id, c.coefficient_number
            LIMIT 1
            """
        ).fetchone()


def _stats(*, power: float, penetration: float, crit_chance: float, crit_damage: float) -> DDStatEvaluation:
    return DDStatEvaluation(
        weapon_damage=power,
        spell_damage=power,
        physical_penetration=penetration,
        spell_penetration=penetration,
        effective_physical_penetration=penetration,
        effective_spell_penetration=penetration,
        physical_overpenetration=0.0,
        spell_overpenetration=0.0,
        critical_chance=crit_chance,
        effective_critical_chance=crit_chance,
        critical_chance_excess=0.0,
        critical_damage=crit_damage,
        effective_critical_damage=crit_damage,
        critical_damage_excess=0.0,
    )


def run_audit(
    database_path: Path,
    *,
    max_stat: float,
    power: float,
    penetration: float,
    crit_chance: float,
    crit_damage: float,
    target_resistance: float,
    target_critical_resistance: float,
) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1

    row = _select_real_component(database_path)
    if row is None:
        print("No persisted complete type-8 damage classification was found.")
        return 2

    coefficient = SkillCoefficient(
        coefficient_number=int(row["coefficient_number"]),
        type=str(row["type"]),
        a=float(row["a"]),
        b=float(row["b"]),
        c=float(row["c"]),
        r=float(row["r"]),
        avg=float(row["avg"]) if row["avg"] is not None else None,
    )
    component = evaluate_skill_coefficient(
        coefficient,
        max_stat=max_stat,
        power=power,
    )
    skill_damage = SkillDamageResult(
        skill_rank_id=int(row["skill_rank_id"]),
        components=(component,),
        total_raw_damage=float(component.scaled_value),
    )

    classification = SkillComponentRepository(database_path).get_component(
        int(row["skill_rank_id"]),
        int(row["coefficient_number"]),
    )
    if classification is None or not classification.is_complete_damage_identity:
        print("Selected database component did not resolve to a complete damage identity.")
        return 3

    mitigation = calculate_dd_mitigation(
        target_resistance=target_resistance,
        penetration=penetration,
    )
    result = calculate_classified_skill_combat_damage(
        skill_damage,
        _stats(
            power=power,
            penetration=penetration,
            crit_chance=crit_chance,
            crit_damage=crit_damage,
        ),
        (classification,),
        mitigation=mitigation,
        combat_state=CombatState(active_buffs=("Major Berserk",)),
        target_combat_state=CombatState(active_buffs=("Major Vulnerability",)),
        target_critical_resistance=target_critical_resistance,
    )

    if result.unresolved or len(result.components) != 1:
        print("End-to-end routing did not resolve exactly one damage component.")
        for message in result.unresolved:
            print(f"  - {message}")
        return 4

    routed = result.components[0].damage

    print("========================================")
    print(" PHASE 3 REAL-DB STATIC DAMAGE AUDIT")
    print("========================================")
    print(f"Database:                   {database_path}")
    print(f"Skill:                      {row['skill_name'] or '(unnamed)'}")
    print(f"Ability ID:                 {row['ability_id']}")
    print(f"Skill rank ID:              {row['skill_rank_id']}")
    print(f"Coefficient:                #{row['coefficient_number']} type {row['type']}")
    print(f"Classification source:      {classification.source or '(unresolved source label)'}")
    print(f"Damage type:                {classification.damage_type}")
    print(f"DoT / AoE / can crit:       {classification.is_dot} / {classification.is_aoe} / {classification.can_crit}")
    print()
    print("Coefficient stage:")
    print(f"  A*MaxStat + B*Power + C:  {component.raw_value:.6f}")
    print(f"  R metadata:               {coefficient.r:.12g} (not applied)")
    print(f"  Routed raw component:     {component.scaled_value:.6f}")
    print()
    print("Combat stages:")
    print(f"  Damage Done multiplier:   {routed.damage_done_multiplier:.6f}")
    print(f"  After Damage Done:        {routed.damage_done_damage:.6f}")
    print(f"  Critical chance:          {routed.critical_chance:.6f}")
    print(f"  Effective crit bonus:     {routed.critical_damage:.6f}")
    print(f"  After expected crit:      {routed.expected_damage:.6f}")
    print(f"  Mitigation multiplier:    {routed.mitigation_multiplier:.6f}")
    print(f"  After mitigation:         {routed.mitigated_damage:.6f}")
    print(f"  Damage Taken multiplier:  {routed.damage_taken_multiplier:.6f}")
    print(f"  Final damage:             {routed.final_damage:.6f}")
    print()
    print("Injected audit state:")
    print("  Attacker: Major Berserk")
    print("  Target:   Major Vulnerability")
    print(f"  Target resistance:        {target_resistance:.0f}")
    print(f"  Penetration:              {penetration:.0f}")
    print(f"  Target Critical Resist:   {target_critical_resistance:.0f}")
    print()
    print("PASS: one persisted real database component traversed the complete Phase 3 static damage pipeline.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Route one persisted real database skill component through the complete Phase 3 static damage pipeline."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--max-stat", type=float, default=30000.0)
    parser.add_argument("--power", type=float, default=4000.0)
    parser.add_argument("--penetration", type=float, default=7000.0)
    parser.add_argument("--crit-chance", type=float, default=50.0)
    parser.add_argument("--crit-damage", type=float, default=75.0)
    parser.add_argument("--target-resistance", type=float, default=18200.0)
    parser.add_argument("--target-critical-resistance", type=float, default=1320.0)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(
        run_audit(
            args.database,
            max_stat=args.max_stat,
            power=args.power,
            penetration=args.penetration,
            crit_chance=args.crit_chance,
            crit_damage=args.crit_damage,
            target_resistance=args.target_resistance,
            target_critical_resistance=args.target_critical_resistance,
        )
    )
