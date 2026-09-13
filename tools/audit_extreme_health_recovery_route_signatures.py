from __future__ import annotations

"""Reduce the complete legal class-route universe by Health Recovery mechanics.

This audit proves structural equivalence only. It does not yet claim a dominant
numeric route because several retained mechanics depend on slot count, runtime
state, missing Health, or Class Mastery execution.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_health_recovery_class_route_signature_service import (
    ExtremeHealthRecoveryClassRouteSignatureService,
)
from services.extreme_passive_projection_service import ExtremePassiveProjectionService
from services.extreme_skill_universe_service import (
    ExtremeSkillDomain,
    ExtremeSkillUniverseService,
)

OBJECTIVE = "health_recovery"

_LINE_MECHANICS = {
    "draconic_power": "Elder Dragon conditional flat ceiling +700",
    "storm_calling": "Capacitor static flat +141",
    "soldier_of_apocrypha": "Wellspring of the Abyss +81 per Soldier ability slotted",
    "living_death": "Undead Confederate conditional flat +155",
}
_MASTERY_MECHANICS = {
    "booming_voice": "Booming Voice recovery scales with Ultimate spent",
    "sphere_of_influence": "Sphere of Influence conditional flat +225",
    "devout_guardian": "Devout Guardian contextual Class Mastery state retained",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _racial_frontier(database: Path):
    passives = tuple(
        row
        for row in ExtremeSkillUniverseService(database).all_player_skills()
        if row.is_passive and row.domain is ExtremeSkillDomain.RACIAL
    )
    positive = []
    unresolved_mentions = []
    for passive in passives:
        projection = ExtremePassiveProjectionService.project(passive)
        contributions = tuple(
            contribution
            for contribution in projection.contributions
            if contribution.objective_key == OBJECTIVE
        )
        if contributions:
            positive.append((passive, contributions))
            continue
        text = f"{passive.name} {passive.description}".casefold()
        if "health recovery" in text or (
            "health" in text and "magicka" in text and "stamina recovery" in text
        ):
            unresolved_mentions.append(passive)
    return passives, tuple(positive), tuple(unresolved_mentions)


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    routes = ExtremeHealClassRouteService().all_routes()
    catalog = ExtremeHealthRecoveryClassRouteSignatureService.build(routes)
    racial_passives, racial_positive, racial_unresolved = _racial_frontier(database)

    print("EXTREME HEALTH RECOVERY RACE + CLASS ROUTE SIGNATURE AUDIT")
    print(f"database={database}")
    print("mode=proof_preserving_signature_reduction_not_numeric_dominance")
    print()

    print("RACE FRONTIER")
    print(f"racial_passives_reviewed={len(racial_passives)}")
    print(f"positive_health_recovery_races={len(racial_positive)}")
    print(f"racial_recovery_unresolved_mentions={len(racial_unresolved)}")
    for passive, contributions in racial_positive:
        total_flat = sum(float(row.flat) for row in contributions)
        total_percent = sum(float(row.percent_of_reference) for row in contributions)
        print(
            f"  race_line={passive.skill_line!r} passive={passive.name!r} "
            f"flat={total_flat:.3f} percent_of_reference={total_percent:.6f}"
        )
    race_dominance_proven = bool(racial_positive) and not racial_unresolved
    print(f"race_dominance_proven={race_dominance_proven}")
    if race_dominance_proven and len(racial_positive) == 1:
        passive, contributions = racial_positive[0]
        print(
            f"race_witness={passive.skill_line.removesuffix(' Skills')!r} "
            f"direct_flat={sum(float(row.flat) for row in contributions):.3f}"
        )
    print()

    print("CLASS ROUTE SIGNATURE REDUCTION")
    print(f"source_class_routes={catalog.source_route_count}")
    print(f"projected_route_signatures={catalog.projected_signature_count}")
    print(f"projection_complete={catalog.projection_complete}")
    print(f"unresolved_count={len(catalog.unresolved)}")
    for item in catalog.unresolved:
        print(f"  unresolved: {item}")
    print()

    for index, group in enumerate(catalog.groups, start=1):
        signature = group.signature
        representative = group.representative
        print(
            f"SIGNATURE {index}: routes={len(group.routes)} "
            f"lines={signature.relevant_skill_lines!r} mastery={signature.class_mastery or '<none>'}"
        )
        print(
            f"  representative=base:{representative.base_class.value} "
            f"equipped:{representative.equipped_skill_lines!r} "
            f"subclassed:{representative.is_subclassed}"
        )
        mechanics = [
            _LINE_MECHANICS[line]
            for line in signature.relevant_skill_lines
            if line in _LINE_MECHANICS
        ]
        if signature.class_mastery in _MASTERY_MECHANICS:
            mechanics.append(_MASTERY_MECHANICS[signature.class_mastery])
        if mechanics:
            for mechanic in mechanics:
                print(f"  mechanic: {mechanic}")
        else:
            print("  mechanic: no class-specific Health Recovery contribution")

    whole_signature_denominator_closed = bool(
        catalog.projection_complete
        and race_dominance_proven
        and not catalog.unresolved
        and not racial_unresolved
    )
    print()
    print(f"race_and_route_signature_denominator_closed={whole_signature_denominator_closed}")
    if not whole_signature_denominator_closed:
        print("NEXT_STEP=close race or route signature evidence before numeric route scoring")
        return 2

    print(
        "NEXT_STEP=resolve retained class runtime ceilings and slot legality, then prove numeric route dominance "
        "across the reduced signatures"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
