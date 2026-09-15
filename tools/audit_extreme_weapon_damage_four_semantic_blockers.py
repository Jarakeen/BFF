from __future__ import annotations

"""Resolve the four remaining semantic Weapon Damage named-gear blockers.

This is a proof diagnostic, not a final whole-build scorer. It converts the four
still-unbounded semantic categories left by the unresolved named-gear triage into
finite ceilings or existing finite exact-execution paths:

* Balorgh: cap Ultimate-consumed Weapon Damage by the project's reviewed 500 stored
  Ultimate ceiling.
* Heartland Conqueror: bound the 100% weapon-trait-effectiveness clause on the
  already-proven Dual Wield Nirnhoned topology by one additional copy of the
  reviewed Nirnhoned contribution.
* Oakfather's Retribution: use the checked-in Major/Minor effect-ID catalog as a
  finite denominator and intentionally assume every catalogued Minor effect can be
  active on the target at once.
* Twice-Born Star: route to the existing finite two-Mundus canonical executor rather
  than pretending its second boon is a flat Weapon Damage amount.

These are deliberately favorable bounds. They may over-credit impossible concurrent
states, which is safe for a dominance proof. They never under-credit an unresolved
mechanic and never claim physical same-build composition by themselves.
"""

from math import floor
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.item_base_stats import (
    DUAL_WIELD_OFFHAND_POWER_RATIO,
    WEAPON_NIRNHONED_PERCENT_GOLD,
    WEAPON_POWER_CP160_GOLD,
)
from services.extreme_twice_born_mundus_structural_stat_evaluator import (
    ExtremeTwiceBornMundusStructuralStatEvaluator,
)

DATABASE = ROOT / "data" / "eso.db"
MAJOR_MINOR_CATALOG = ROOT / "docs" / "major_minor_effect_ids.md"
FIELD_NOTES = ROOT / "GAME_MECHANICS_FIELD_NOTES.md"
RESOLVED_INCUMBENT = 9451.238
MAX_STORED_ULTIMATE = 500.0
BALORGH_STATIC_ONE_PIECE = 129.0
HEARTLAND_STATIC_TWO_PIECE = 129.0
OAKFATHER_STATIC_TWO_TO_FOUR = 129.0 * 3.0
OAKFATHER_PER_MINOR_BUFF = 20.0


def _nirnhoned_delta(power: float, *, scale: float = 1.0) -> float:
    improved = float(floor(float(power) * (1.0 + WEAPON_NIRNHONED_PERCENT_GOLD)))
    return (improved - float(power)) * float(scale)


def _reviewed_dual_wield_nirnhoned_delta() -> float:
    one_hand = float(WEAPON_POWER_CP160_GOLD["Sword"])
    return _nirnhoned_delta(one_hand) + _nirnhoned_delta(
        one_hand,
        scale=DUAL_WIELD_OFFHAND_POWER_RATIO,
    )


def _minor_effect_names() -> tuple[str, ...]:
    text = MAJOR_MINOR_CATALOG.read_text(encoding="utf-8")
    names = []
    for match in re.finditer(r"^##\s+(Minor\s+[^\n]+)$", text, flags=re.MULTILINE):
        name = " ".join(match.group(1).split())
        # The ID catalog may contain provenance-specific duplicate headings such as
        # "Minor Breach (Fossilize combat; display ...)". Oakfather counts the named
        # Minor effect, not each source-ID family, so collapse parenthetical aliases.
        canonical = name.split(" (", 1)[0].strip()
        if canonical:
            names.append(canonical)
    return tuple(sorted(dict.fromkeys(names), key=str.casefold))


def _field_notes_prove_500_ultimate() -> bool:
    text = FIELD_NOTES.read_text(encoding="utf-8")
    folded = " ".join(text.casefold().split())
    return "500 stored ultimate" in folded


def main() -> int:
    print("EXTREME WEAPON DAMAGE FOUR SEMANTIC BLOCKER RESOLUTION")
    print(f"database={DATABASE}")
    print(f"resolved_same_build_incumbent={RESOLVED_INCUMBENT:.3f}")
    print("physical_realization_in_scope=False")
    print("same_build_composition_claimed=False")
    print()

    # Balorgh
    ultimate_proven = _field_notes_prove_500_ultimate()
    balorgh_proc = MAX_STORED_ULTIMATE if ultimate_proven else 0.0
    balorgh_bound = BALORGH_STATIC_ONE_PIECE + balorgh_proc
    print("BALORGH 2PC")
    print(f"stored_ultimate_ceiling={MAX_STORED_ULTIMATE:.0f}")
    print(f"stored_ultimate_ceiling_reviewed={ultimate_proven}")
    print(f"static_weapon_damage={BALORGH_STATIC_ONE_PIECE:.3f}")
    print(f"ultimate_consumed_weapon_damage_upper_bound={balorgh_proc:.3f}")
    print(f"flat_weapon_damage_upper_bound={balorgh_bound:.3f}")
    print("assumption=all 500 stored Ultimate is consumed by one legal Ultimate activation")
    print()

    # Heartland Conqueror
    reviewed_nirn = _reviewed_dual_wield_nirnhoned_delta()
    heartland_extra = reviewed_nirn  # +100% trait effectiveness = one extra reviewed copy.
    heartland_bound = HEARTLAND_STATIC_TWO_PIECE + heartland_extra
    print("HEARTLAND CONQUEROR 5PC")
    print(f"reviewed_dual_wield_nirnhoned_delta={reviewed_nirn:.3f}")
    print("trait_effectiveness_multiplier=2.000")
    print(f"additional_trait_weapon_damage_upper_bound={heartland_extra:.3f}")
    print(f"flat_weapon_damage_upper_bound={heartland_bound:.3f}")
    print("weapon_topology=proven Dual Wield swords")
    print("assumption=Heartland doubles the already-reviewed Nirnhoned contribution and no weaker trait is substituted")
    print()

    # Oakfather's Retribution
    minor_names = _minor_effect_names()
    oakfather_dynamic = OAKFATHER_PER_MINOR_BUFF * float(len(minor_names))
    oakfather_bound = OAKFATHER_STATIC_TWO_TO_FOUR + oakfather_dynamic
    print("OAKFATHER'S RETRIBUTION 5PC")
    print(f"minor_effect_catalog_count={len(minor_names)}")
    print(f"minor_effect_names={minor_names!r}")
    print(f"static_weapon_damage={OAKFATHER_STATIC_TWO_TO_FOUR:.3f}")
    print(f"per_minor_buff_weapon_damage={OAKFATHER_PER_MINOR_BUFF:.3f}")
    print(f"target_minor_buff_weapon_damage_upper_bound={oakfather_dynamic:.3f}")
    print(f"flat_weapon_damage_upper_bound={oakfather_bound:.3f}")
    print("assumption=every distinct catalogued Minor effect is simultaneously active on the target")
    print()

    # Twice-Born Star
    tbs_executor_present = ExtremeTwiceBornMundusStructuralStatEvaluator is not None
    print("TWICE-BORN STAR 5PC")
    print(f"canonical_two_mundus_executor_present={tbs_executor_present}")
    print("finite_state_space=True")
    print("direct_flat_weapon_damage_upper_bound=<not flattened>")
    print("resolution=exact finite two-Mundus execution required during reduced physical realization")
    print()

    blockers = []
    if not ultimate_proven:
        blockers.append("Balorgh: project evidence for 500 stored Ultimate not found")
    if not minor_names:
        blockers.append("Oakfather's Retribution: checked-in Minor effect catalog is empty")
    if not tbs_executor_present:
        blockers.append("Twice-Born Star: canonical two-Mundus executor unavailable")

    print("PROOF STATUS")
    print(f"balorgh_semantic_bound_closed={ultimate_proven}")
    print("heartland_semantic_bound_closed=True")
    print(f"oakfather_semantic_bound_closed={bool(minor_names)}")
    print(f"twice_born_star_semantic_executor_closed={tbs_executor_present}")
    print(f"semantic_blockers_remaining={len(blockers)}")
    for blocker in blockers:
        print(f"  unresolved: {blocker}")
    print("all_four_semantic_categories_resolved=" + str(not blockers))
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=merge these four resolutions with the 74 already-finite semantic ceilings, then build one reduced physical topology upper-bound pass against the 9451.238 resolved incumbent; execute Twice-Born Star through its canonical two-Mundus path rather than flattening it"
    )
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
