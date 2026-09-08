from __future__ import annotations

"""Read-only audit for reviewed Sorcerer healing candidates.

The audit prints the concrete max-rank/morph row, coefficient formulas, current
component classification, and coefficient-local UESP-derived wording for the
Sorcerer healing families most relevant to Extreme Actual Heal. It never writes
``eso.db`` and does not infer recipient/time identity from row order or magnitude.
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
    "Dark Exchange",
    "Dark Conversion",
    "Dark Deal",
    "Summon Winged Twilight",
    "Summon Twilight Matriarch",
    "Summon Unstable Clannfear",
    "Regenerative Ward",
    "Surge",
    "Critical Surge",
    "Power Surge",
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


def _fmt_optional(value: bool | None) -> str:
    return "yes" if value is True else "no" if value is False else "unknown"


def audit(*, database_path: Path) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1

    coefficients = SkillCoefficientRepository(database_path)
    components = SkillComponentRepository(database_path)

    print("========================================")
    print(" EXTREME SORCERER HEALING IDENTITY AUDIT")
    print("========================================")
    print(f"Database: {database_path}")
    print("Boundary: read-only; trigger/proc mechanics are not promoted to direct HEAL events")

    found = 0
    seen_skill_ranks: set[int] = set()
    missing: list[str] = []
    for requested_name in ABILITY_NAMES:
        resolution = coefficients.resolve_name(requested_name)
        if resolution.rank is None:
            missing.append(requested_name)
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
            classification = (
                "unclassified" if identity is None else identity.effect_kind.value
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
                    crit=_fmt_optional(None if identity is None else identity.can_crit),
                    dot=_fmt_optional(None if identity is None else identity.is_dot),
                    aoe=_fmt_optional(None if identity is None else identity.is_aoe),
                )
            )
            print(f"      text: {evidence.fragment or '(no coefficient-local text)'}")
            if evidence.evidence:
                print("      evidence: " + "; ".join(evidence.evidence))

    if missing:
        print()
        print("Unresolved by canonical name:")
        for name in missing:
            print(f"  - {name}")

    if not found:
        print()
        print("No reviewed Sorcerer healing candidate ranks were resolved.")
        return 2

    print()
    print("Passive/trigger boundary:")
    print("  - Blood Magic is a passive-triggered self heal and is not expected to resolve as a normal skill coefficient row here.")
    print("  - Surge/Critical Surge/Power Surge may expose trigger-conditioned healing; do not treat their activation cast as the heal event unless coefficient evidence proves it.")
    print("  - Pet activation heals require recipient identity for player, ally, and pet targets before one-recipient Actual Heal scoring.")
    print("  - Missing or ambiguous event identity remains unresolved rather than inferred.")
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
