from __future__ import annotations

"""Read-only audit for Dragon Blood-family HEAL component identity.

The audit prints the exact canonical rank/morph, coefficient rows, current
component classification, and coefficient-local UESP-derived wording for the
Dragon Blood family.  It never writes ``eso.db``.  The purpose is to gather the
per-coefficient evidence needed to assign recipient/time identity without
inferring from coefficient order.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_repository import SkillComponentRepository
from minmax.skill_component_text_evidence import extract_component_text_evidence

ABILITY_NAMES = (
    "Dragon Blood",
    "Blood of the Green Dragon",
    "Green Dragon Blood",
    "Blood of the Elder Dragon",
    "Coagulating Blood",
)


def _coef_description(database_path: Path, skill_rank_id: int) -> str:
    with sqlite3.connect(database_path) as db:
        row = db.execute(
            """
            SELECT a.coef_description
            FROM skill_rank sr
            LEFT JOIN ability a ON a.ability_id = sr.ability_id
            WHERE sr.id = ?
            """,
            (int(skill_rank_id),),
        ).fetchone()
    return "" if row is None else str(row[0] or "")


def audit(*, database_path: Path) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1

    coefficients = SkillCoefficientRepository(database_path)
    components = SkillComponentRepository(database_path)

    print("============================================")
    print(" EXTREME DRAGON BLOOD HEAL IDENTITY AUDIT")
    print("============================================")
    print(f"Database: {database_path}")
    print("Boundary: read-only; no coefficient identity is inferred from row order")

    found = 0
    seen_skill_ranks: set[int] = set()
    for requested_name in ABILITY_NAMES:
        resolution = coefficients.resolve_name(requested_name)
        if resolution.rank is None:
            continue
        rank = resolution.rank
        if rank.skill_rank_id in seen_skill_ranks:
            continue
        seen_skill_ranks.add(rank.skill_rank_id)
        found += 1

        description = _coef_description(database_path, rank.skill_rank_id)
        classified = {
            int(row.coefficient_number): row
            for row in components.get_for_skill_rank(rank.skill_rank_id)
        }

        print()
        print(
            f"{rank.name} | entity={rank.entity_id} | rank={rank.rank} | morph={rank.morph} | "
            f"skill_rank_id={rank.skill_rank_id} | ability_id={rank.ability_id}"
        )
        print(f"coef_description: {description or '(empty)'}")

        if not rank.coefficients:
            print("  coefficients: none")
            continue

        for coefficient in rank.coefficients:
            number = int(coefficient.coefficient_number)
            identity = classified.get(number)
            evidence = extract_component_text_evidence(description, number)
            if identity is None:
                classification = "unclassified"
                crit = "unknown"
                is_dot = "unknown"
                is_aoe = "unknown"
            else:
                classification = identity.effect_kind.value
                crit = (
                    "yes" if identity.can_crit is True else "no" if identity.can_crit is False else "unknown"
                )
                is_dot = (
                    "yes" if identity.is_dot is True else "no" if identity.is_dot is False else "unknown"
                )
                is_aoe = (
                    "yes" if identity.is_aoe is True else "no" if identity.is_aoe is False else "unknown"
                )

            print(
                "  - coef #{number} | type={type} | a={a:.9g} | b={b:.9g} | c={c:.9g} | "
                "r={r:.9g} | kind={kind} | can_crit={crit} | periodic={dot} | aoe={aoe}".format(
                    number=number,
                    type=coefficient.type,
                    a=coefficient.a,
                    b=coefficient.b,
                    c=coefficient.c,
                    r=coefficient.r,
                    kind=classification,
                    crit=crit,
                    dot=is_dot,
                    aoe=is_aoe,
                )
            )
            print(f"      text: {evidence.fragment or '(no coefficient-local text)'}")
            if evidence.evidence:
                print("      evidence: " + "; ".join(evidence.evidence))

    if not found:
        print()
        print("No Dragon Blood-family canonical skill ranks were resolved.")
        return 2

    print()
    print("Interpretation boundary:")
    print("  - Do not assign recipient identity from coefficient number or magnitude alone.")
    print("  - Coefficient-local wording may prove self/ally and direct/periodic scope.")
    print("  - Ambiguous rows remain unresolved until corroborating evidence exists.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_DATABASE),
        help="Path to eso.db (default: canonical data/eso.db)",
    )
    args = parser.parse_args()
    return audit(database_path=args.database)


if __name__ == "__main__":
    raise SystemExit(main())
