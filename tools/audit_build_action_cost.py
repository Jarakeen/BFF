from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.build_final_action_cost import BuildFinalActionCostResolver
from minmax.character_progression import CharacterProgression
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.resource_costs import ResourceType, resolve_base_action_cost
from models.build_model import PlayerBuild


def _load_build(path: Path, build_name: str) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    members = payload.get("Members", [])
    target = str(build_name or "").strip().casefold()
    for member in members:
        candidate = str(member.get("BuildName", "") or "").strip()
        if candidate.casefold() == target:
            return PlayerBuild.from_dict(member)
    raise ValueError(f"Saved build not found: {build_name}")


def _ability_row(connection: sqlite3.Connection, ability_id: int) -> tuple:
    row = connection.execute(
        """
        SELECT id, name, rank, morph, base_cost, base_mechanic, skill_line
        FROM ability
        WHERE id = ?
        """,
        (ability_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Ability not found: {ability_id}")
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit saved-build Phase 4 action cost inputs and output")
    parser.add_argument("--build", required=True)
    parser.add_argument("--ability-id", required=True, type=int)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--builds", default=str(ROOT / "data" / "builds.json"))
    parser.add_argument(
        "--owned-skill-line",
        action="append",
        default=[],
        help="Explicit owned skill line for passive gating; repeat as needed",
    )
    args = parser.parse_args()

    database = Path(args.database)
    builds = Path(args.builds)
    build = _load_build(builds, args.build)
    progression = CharacterProgression(owned_skill_lines=tuple(args.owned_skill_line))

    with sqlite3.connect(database) as connection:
        ability_id, ability_name, rank, morph, base_cost, base_mechanic, skill_line = _ability_row(
            connection, args.ability_id
        )

    base = resolve_base_action_cost(
        ability_id=ability_id,
        base_cost=base_cost,
        base_mechanic=base_mechanic,
        rank=rank,
        morph=morph,
    )

    modifier_resolver = BuildActionCostModifierResolver(
        JewelryCostModifierRepository(database),
        JewelryTraitRepository(database),
    )
    final_resolver = BuildFinalActionCostResolver(modifier_resolver)
    result = final_resolver.resolve(
        build,
        base,
        skill_line=skill_line,
        progression=progression,
    )

    print("=" * 48)
    print(" PHASE 4 SAVED-BUILD ACTION COST AUDIT")
    print("=" * 48)
    print(f"Build:          {build.BuildName}")
    print(f"Character:      {build.Name}")
    print(f"Race:           {build.Race}")
    print(f"Ability:        {ability_name}")
    print(f"Ability ID:     {ability_id}")
    print(f"Rank / morph:   {rank} / {morph}")
    print(f"Skill line:     {skill_line or 'unresolved'}")
    print(f"Base cost:      {base.amount:g}")
    print("Resources:      " + ", ".join(resource.value for resource in base.resources))
    print("Owned lines:    " + (", ".join(progression.owned_skill_lines) or "none supplied"))
    print()
    print("MODIFIERS")
    print("---------")
    if not result.modifiers.modifiers:
        print("none")
    else:
        for modifier in result.modifiers.modifiers:
            resources = ",".join(resource.value for resource in modifier.resources)
            scope = ",".join(modifier.skill_lines) if modifier.skill_lines else "all eligible skill lines"
            print(
                f"{modifier.source}: {modifier.operation.value}={modifier.value:g} "
                f"resources={resources} scope={scope}"
            )

    print()
    if result.unresolved:
        print("UNRESOLVED")
        print("----------")
        for item in result.unresolved:
            print(item)
        return 2

    assert result.final_cost is not None
    print("FINAL COST")
    print("----------")
    for item in result.final_cost.resource_costs:
        print(
            f"{item.resource.value}: base={item.base_amount:g} "
            f"flat={item.flat_reduction:g} percent={item.percent_reduction:g} "
            f"raw={item.raw_amount:.6f} final={item.final_amount}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
