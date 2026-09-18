from __future__ import annotations

"""Audit E2 legal-character search coverage for Extreme MOST Actual Heal.

This audit is metadata-only and read-only. It does not score a build, touch the
canonical database, or promote partial search support into a global-maximum claim.
Its purpose is to keep the E2 roadmap denominator explicit: every required legal
character dimension is listed with its current integration state, canonical owner,
and the exact proof gap that still prevents closure.

The rows intentionally distinguish structural search from mechanic proof. For
example, class/subclass routes can be structurally exhaustive while class-passive
mechanic coverage on those routes is still incomplete.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogService,
)
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
from services.extreme_actual_heal_trait_denominator_service import (
    ExtremeActualHealTraitDenominatorService,
)
from services.extreme_canonical_actual_heal_optimization_service import (
    ExtremeCanonicalActualHealOptimizationService,
)


class E2DimensionStatus(str, Enum):
    COVERED = "covered"
    CONDITIONAL = "conditional"
    PARTIAL = "partial"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class E2DimensionCoverage:
    key: str
    label: str
    status: E2DimensionStatus
    owner: str
    evidence: str
    remaining_gap: str = ""


_REQUIRED_DIMENSION_KEYS = (
    "race",
    "class_route",
    "progression_passives",
    "attributes",
    "mundus",
    "food_drink",
    "potion_state",
    "armor_weights_passives",
    "gear_packages_procs",
    "traits",
    "glyphs_enchantments",
    "weapon_configuration_passives",
    "skills_morphs_ultimates",
    "champion_points",
    "class_mastery",
    "runtime_event_state",
)


def _scope_contains(scope: tuple[str, ...], *needles: str) -> bool:
    text = "\n".join(str(item).casefold() for item in scope)
    return all(str(needle).casefold() in text for needle in needles)


def build_dimension_coverage() -> tuple[E2DimensionCoverage, ...]:
    """Return the conservative H1/E2 legal-dimension ledger.

    Statuses describe proof maturity, not whether some code exists. ``covered``
    is reserved for dimensions whose current owner explicitly enumerates the
    relevant legal axis for H1. ``partial`` means useful search exists but the
    denominator or mechanic family is not yet fully closed. ``conditional`` means
    the dimension is supported only when explicit scenario/runtime evidence is
    supplied. ``blocked`` is reserved for a known missing prerequisite.
    """

    optimization_scope = tuple(ExtremeActualHealOptimizationService.SEARCH_SCOPE)
    optimization_omitted = tuple(ExtremeActualHealOptimizationService.OMITTED_SCOPE)
    route_scope = tuple(ExtremeActualHealClassRouteCatalogService.SEARCH_SCOPE)
    route_omitted = tuple(ExtremeActualHealClassRouteCatalogService.OMITTED_SCOPE)

    rows = (
        E2DimensionCoverage(
            "race",
            "Race",
            E2DimensionStatus.COVERED,
            "ExtremeActualHealOptimizationService._race_candidates",
            "RaceRepository.list_races is materialized onto whole-build candidates and rescored canonically.",
        ),
        E2DimensionCoverage(
            "class_route",
            "Base class + legal subclass route",
            E2DimensionStatus.COVERED,
            "ExtremeActualHealClassRouteCatalogService",
            "Structurally legal three-class-line routes are exhaustively enumerated; base-class widening is explicitly supported.",
        ),
        E2DimensionCoverage(
            "progression_passives",
            "Character progression + class passives",
            E2DimensionStatus.PARTIAL,
            "ExtremeHypotheticalClassProgressionService + class passive coverage inventory",
            "Selected-route progression is normalized to canonical maximum ranks.",
            "Complete class-line passive/proc mechanic coverage remains explicit omitted scope.",
        ),
        E2DimensionCoverage(
            "attributes",
            "Attributes",
            E2DimensionStatus.COVERED,
            "ExtremeActualHealAttributeProjectionService + ExtremeCanonicalActualHealOptimizationService",
            "The complete 2,145-allocation 64-point simplex remains the denominator and is proof-reduced to pure Magicka/Stamina endpoints only for the reviewed standing type-8 highest-resource H1 coefficient path; unsupported coefficient families fail closed to the conservative candidate path.",
        ),
        E2DimensionCoverage(
            "mundus",
            "Mundus",
            E2DimensionStatus.COVERED,
            "ExtremeCompleteOptimizationService",
            "Mundus is an explicit whole-build search axis in H1 and is rescored through canonical healing math.",
        ),
        E2DimensionCoverage(
            "food_drink",
            "Food / drink",
            E2DimensionStatus.COVERED,
            "ExtremeCompleteOptimizationService",
            "Food/drink is an explicit whole-build H1 search axis.",
        ),
        E2DimensionCoverage(
            "potion_state",
            "Potion capability + explicit use state",
            E2DimensionStatus.CONDITIONAL,
            "ExtremeActualHealPotionCandidateService + ExtremeRuntimeSnapshot",
            "Potion families are searchable inside an explicit potion-use runtime scenario.",
            "Standing H1 search intentionally does not invent potion uptime or use state.",
        ),
        E2DimensionCoverage(
            "armor_weights_passives",
            "Armor weights + armor passives",
            E2DimensionStatus.COVERED,
            "ExtremeActualHealArmorWeightLegalityService + ExtremeActualHealArmorWeightCandidateService + ExtremeCanonicalActualHealOptimizationService",
            "Every current-layout and armor-bearing package candidate is expanded through canonical gear_set_piece slot/armor_type legality, the full legal per-slot weight product is counted, and one deterministic witness is retained for every H1-relevant (Medium-piece count, distinct armor-type count) signature before canonical healing rescoring. This preserves the reviewed Agility/Dexterity and Undaunted Mettle inputs without treating cosmetic slot permutations as separate mechanics.",
        ),
        E2DimensionCoverage(
            "gear_packages_procs",
            "Gear sets / mythics / monster sets / arena weapons / procs",
            E2DimensionStatus.PARTIAL,
            "ExtremeActualHealGearDenominatorService + actual-heal gear package services + runtime gear-proc evidence",
            "The complete canonical ordinary-set corpus now receives one reconciled H1 disposition and accepted rows are cross-checked against the authoritative five-piece candidate pool; reviewed monster, double-five, mythic, non-ring mythic, arena-weapon, and explicit runtime proc paths also exist.",
            "Ordinary five-piece accounting is explicit, but monster/mythic/arena/proc package families do not yet each expose a complete canonical denominator and disposition reconciliation for H1.",
        ),
        E2DimensionCoverage(
            "traits",
            "Armor / jewelry / weapon traits",
            E2DimensionStatus.COVERED,
            "ExtremeActualHealTraitDenominatorService + ExtremeCompleteOptimizationService",
            "All 27 canonical nonblank trait values are dispositioned for H1: 24 are searched directly and Sturdy, Well-Fitted, and Training are explicitly pruned as unable to change one reviewed healing-event magnitude. The proof is per-slot/value; Cartesian-product proof remains an E4 search-space concern.",
        ),
        E2DimensionCoverage(
            "glyphs_enchantments",
            "Glyphs / enchantments",
            E2DimensionStatus.COVERED,
            "ExtremeActualHealStaticEnchantDenominatorService + ExtremeCompleteOptimizationService",
            "The static H1 denominator closes all 24 canonical armor/jewelry enchant families: 4 armor families are searched, 5 jewelry families are searched, and 15 jewelry families are explicitly dispositioned as irrelevant to one instantaneous healing-event magnitude. Weapon enchantments remain correctly owned by the runtime proc/cooldown/trigger boundary rather than this static denominator.",
        ),
        E2DimensionCoverage(
            "weapon_configuration_passives",
            "Front/back weapon configuration + weapon passives",
            E2DimensionStatus.PARTIAL,
            "ExtremeActualHealClassRouteCatalogService + arena/mythic weapon package services",
            "Weapon-skill heal legality and exact active-weapon subtype requirements are enforced for reviewed candidates.",
            "H1 does not yet enumerate the complete legal front/back weapon-configuration axis and all weapon-passive consequences.",
        ),
        E2DimensionCoverage(
            "skills_morphs_ultimates",
            "Active skills / morphs / ultimates / standing effects",
            E2DimensionStatus.PARTIAL,
            "ExtremeHealSkillCandidateService + ExtremeActualHealClassRouteCatalogService",
            "Selected HEAL replacement is searched across the five ordinary active-bar slots while preserving ultimate identity.",
            "Full multi-skill front/back-bar combinatorial search, ultimate replacement, and all standing/slotted effect families remain open.",
        ),
        E2DimensionCoverage(
            "champion_points",
            "Champion Points",
            E2DimensionStatus.PARTIAL,
            "ExtremeActualHealChampionPointCandidateService + ExtremeCanonicalActualHealOptimizationService",
            "Reviewed heal-magnitude CP stars are discovered, legal loadouts are enumerated, and mixed units are compared only after canonical heal scoring.",
            "Real-build H1 closure is still blocked on positive canonical critical-heal evidence for at least one saved-build witness; global CP/mechanic denominator reporting is not yet closed.",
        ),
        E2DimensionCoverage(
            "class_mastery",
            "Class Mastery",
            E2DimensionStatus.CONDITIONAL,
            "Class Mastery classification + reviewed class-specific healing services",
            "Reviewed Class Mastery effects such as Nightblade target-health scaling are consumed when their exact scenario prerequisites are supplied.",
            "Cross-class Class Mastery search is not yet a complete H1 denominator.",
        ),
        E2DimensionCoverage(
            "runtime_event_state",
            "Exact event/runtime state",
            E2DimensionStatus.CONDITIONAL,
            "ExtremeRuntimeSnapshot + ExtremeRuntimeSnapshotCombatStateService",
            "E1 closed the shared role-neutral runtime timeline for reviewed named buffs, timed effects, potion windows, triggered skills, gear procs, conditions, cooldowns, stacking, and bar provenance.",
            "H1 must still search or explicitly select the objective-specific scenario state; standing search may not invent conditional uptime.",
        ),
    )

    if tuple(row.key for row in rows) != _REQUIRED_DIMENSION_KEYS:
        raise AssertionError("Extreme E2 H1 dimension ledger drifted from the required roadmap denominator")

    # Fail loudly if core owners stop advertising dimensions this ledger relies on.
    required_scope_checks = (
        (_scope_contains(optimization_scope, "race"), "H1 race search scope disappeared"),
        (_scope_contains(optimization_scope, "attribute allocation"), "H1 attribute search scope disappeared"),
        (_scope_contains(optimization_scope, "mundus"), "H1 Mundus search scope disappeared"),
        (_scope_contains(optimization_scope, "food/drink"), "H1 food/drink search scope disappeared"),
        (_scope_contains(optimization_scope, "armor traits"), "H1 armor-trait search scope disappeared"),
        (_scope_contains(optimization_scope, "jewelry traits"), "H1 jewelry-trait search scope disappeared"),
        (_scope_contains(optimization_scope, "weapon traits"), "H1 weapon-trait search scope disappeared"),
        (_scope_contains(route_scope, "structurally legal class-line routes"), "H1 class-route search scope disappeared"),
        (_scope_contains(route_scope, "selected heal replacement"), "H1 selected-heal search scope disappeared"),
        (_scope_contains(route_omitted, "full multi-skill"), "H1 multi-skill omission boundary disappeared without ledger review"),
        (_scope_contains(route_omitted, "passive/proc coverage"), "H1 passive/proc omission boundary disappeared without ledger review"),
        (_scope_contains(optimization_omitted, "runtime conditional"), "H1 standing-runtime omission boundary disappeared without ledger review"),
    )
    failed = tuple(message for passed, message in required_scope_checks if not passed)
    if failed:
        raise AssertionError("; ".join(failed))

    if ExtremeCanonicalActualHealOptimizationService.CP_SEARCH_SCOPE != (
        "legal heal-relevant Champion Point loadout search"
    ):
        raise AssertionError("Extreme H1 Champion Point search contract changed without E2 ledger review")

    trait_denominator = ExtremeActualHealTraitDenominatorService().build()
    if not trait_denominator.denominator_proven:
        raise AssertionError(
            "Extreme H1 trait denominator is not proven: "
            + "; ".join(trait_denominator.unresolved)
        )
    if trait_denominator.legal_trait_value_count != 27:
        raise AssertionError(
            "Extreme H1 canonical trait-value denominator changed without E2 ledger review"
        )

    return rows


def main() -> int:
    rows = build_dimension_coverage()
    counts = {status: 0 for status in E2DimensionStatus}
    for row in rows:
        counts[row.status] += 1

    print("EXTREME E2 ACTUAL HEAL LEGAL-DIMENSION COVERAGE")
    print()
    for row in rows:
        print(f"[{row.status.value.upper():11}] {row.label}")
        print(f"  owner={row.owner}")
        print(f"  evidence={row.evidence}")
        if row.remaining_gap:
            print(f"  gap={row.remaining_gap}")
    print()
    print("SUMMARY")
    print(f"required_dimension_count={len(rows)}")
    for status in E2DimensionStatus:
        print(f"{status.value}_count={counts[status]}")
    denominator_proven = all(row.status is E2DimensionStatus.COVERED for row in rows)
    print(f"e2_actual_heal_dimension_denominator_proven={denominator_proven}")
    print(
        "NEXT_STEP=close PARTIAL dimensions with denominator/disposition proof; "
        "preserve CONDITIONAL dimensions as explicit scenario requirements rather than inventing uptime"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
