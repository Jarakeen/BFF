from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.resource_cost_formula_candidates import (
    evaluate_cost_formula_candidates,
    matching_candidates,
)
from minmax.resource_costs import decode_resource_mechanic


DEFAULT_DATABASE = ROOT / "data" / "eso.db"


def _ability_rows(
    connection: sqlite3.Connection,
    *,
    name: str | None = None,
    ability_id: int | None = None,
) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row

    if ability_id is not None:
        return connection.execute(
            """
            SELECT ability_id, name, rank, morph, skill_line,
                   base_cost, base_mechanic
            FROM ability
            WHERE ability_id = ?
              AND base_cost > 0
            ORDER BY rank, morph, ability_id
            """,
            (ability_id,),
        ).fetchall()

    return connection.execute(
        """
        SELECT ability_id, name, rank, morph, skill_line,
               base_cost, base_mechanic
        FROM ability
        WHERE name = ? COLLATE NOCASE
          AND base_cost > 0
        ORDER BY rank, morph, ability_id
        """,
        (str(name or "").strip(),),
    ).fetchall()


def evaluate_database_ability(
    database_path: str | Path,
    *,
    name: str | None = None,
    ability_id: int | None = None,
    rank: int | None = None,
    morph: int | None = None,
    flat_reduction: float = 0.0,
    percent_reduction: float = 0.0,
    percent_increase: float = 0.0,
    observed_cost: int | None = None,
) -> dict[str, object]:
    if ability_id is None and not str(name or "").strip():
        raise ValueError("Provide either ability_id or exact ability name")

    with sqlite3.connect(str(database_path)) as connection:
        rows = _ability_rows(connection, name=name, ability_id=ability_id)

    if rank is not None:
        rows = [row for row in rows if row["rank"] == rank]
    if morph is not None:
        rows = [row for row in rows if row["morph"] == morph]

    if not rows:
        raise ValueError("No positive-cost ability row matched the requested identity")
    if len(rows) != 1:
        identities = [
            {
                "ability_id": row["ability_id"],
                "name": row["name"],
                "rank": row["rank"],
                "morph": row["morph"],
                "base_cost": row["base_cost"],
            }
            for row in rows
        ]
        raise ValueError(
            "Ability identity is ambiguous; supply --ability-id or --rank/--morph. "
            f"Matches: {identities}"
        )

    row = rows[0]
    resources = tuple(resource.value for resource in decode_resource_mechanic(int(row["base_mechanic"])))
    candidates = evaluate_cost_formula_candidates(
        base_cost=float(row["base_cost"]),
        flat_reduction=flat_reduction,
        percent_reduction=percent_reduction,
        percent_increase=percent_increase,
    )
    matches = (
        matching_candidates(candidates, observed_cost)
        if observed_cost is not None
        else ()
    )

    return {
        "ability_id": row["ability_id"],
        "name": row["name"],
        "rank": row["rank"],
        "morph": row["morph"],
        "skill_line": row["skill_line"],
        "base_cost": float(row["base_cost"]),
        "base_mechanic": int(row["base_mechanic"]),
        "resources": resources,
        "flat_reduction": float(flat_reduction),
        "percent_reduction": float(percent_reduction),
        "percent_increase": float(percent_increase),
        "observed_cost": observed_cost,
        "candidates": candidates,
        "matches": matches,
    }


def _print_report(report: dict[str, object]) -> None:
    print("========================================")
    print(" PHASE 4 ACTION COST FORMULA PROBE")
    print("========================================")
    print(f"Ability:          {report['name']}")
    print(f"Ability ID:       {report['ability_id']}")
    print(f"Rank / morph:     {report['rank']} / {report['morph']}")
    print(f"Skill line:       {report['skill_line'] or 'unresolved'}")
    print(f"Base cost:        {report['base_cost']:g}")
    print(f"Base mechanic:    {report['base_mechanic']}")
    print(f"Resources:        {', '.join(report['resources'])}")
    print(f"Flat reduction:   {report['flat_reduction']:g}")
    print(f"Percent reduction:{report['percent_reduction']:.6f}")
    print(f"Percent increase: {report['percent_increase']:.6f}")
    print(f"Observed cost:    {report['observed_cost'] if report['observed_cost'] is not None else 'not supplied'}")

    print()
    print("CANDIDATES")
    print("----------")
    for candidate in report["candidates"]:
        print(
            f"{candidate.name}: raw={candidate.raw_value:.6f} | "
            f"floor={candidate.floor} | nearest-half-up={candidate.nearest_half_up} | "
            f"ceiling={candidate.ceiling}"
        )

    print()
    print("EXACT MATCHES")
    print("-------------")
    if report["observed_cost"] is None:
        print("observed cost not supplied")
    elif report["matches"]:
        for formula, rounding in report["matches"]:
            print(f"{formula} + {rounding}")
    else:
        print("none")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare candidate ESO action-cost formulas to an observed cost."
    )
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--name", help="Exact ability name")
    identity.add_argument("--ability-id", type=int)
    parser.add_argument("--rank", type=int)
    parser.add_argument("--morph", type=int)
    parser.add_argument("--flat-reduction", type=float, default=0.0)
    parser.add_argument("--percent-reduction", type=float, default=0.0)
    parser.add_argument("--percent-increase", type=float, default=0.0)
    parser.add_argument("--observed-cost", type=int)
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    args = parser.parse_args()

    try:
        report = evaluate_database_ability(
            args.database,
            name=args.name,
            ability_id=args.ability_id,
            rank=args.rank,
            morph=args.morph,
            flat_reduction=args.flat_reduction,
            percent_reduction=args.percent_reduction,
            percent_increase=args.percent_increase,
            observed_cost=args.observed_cost,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    _print_report(report)
    if args.observed_cost is not None and not report["matches"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
