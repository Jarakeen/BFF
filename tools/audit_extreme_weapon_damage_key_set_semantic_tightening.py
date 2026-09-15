from __future__ import annotations

"""Tighten recurring Weapon Damage survivor mechanics without changing core scoring.

The generic semantic upper-bound parser intentionally over-credits ambiguous tooltip
numbers. That is useful for fail-closed pruning, but several recurring survivors now
have enough reviewed semantics to use sharper proof-safe ceilings:

* Dreugh King Slayer 5pc: 258 static Weapon/Spell Damage plus one 20% Major
  Brutality/Sorcery named-power ceiling. Major Brutality and Major Sorcery are one
  hybridized named-power state for this objective, not two independent +20% Weapon
  Damage multipliers.
* Nix-Hound's Howl 5pc: 387 static Weapon/Spell Damage. Its Major Courage duplicates
  the already-reviewed Major Courage in the non-gear Weapon Damage baseline. Tooltip
  duration scaling (1 second per 1000 Weapon Damage) is not a power grant.
* Spell Power Cure 5pc: 129 static Weapon/Spell Damage. Its Major Courage duplicates
  the already-reviewed Major Courage baseline.
* Dagon's Dominion 5pc: 258 static universal Weapon/Spell Damage. The additional 492
  applies only to area-of-effect abilities and therefore cannot increase the sheet
  Weapon Damage record.

This wrapper also retains the resource-only metadata reconciliation from the corrected
same-build tightening audit. All other set mechanics keep their previous favorable
semantic upper bounds. A state pruned after these corrections remains proof-safe;
survivors still require exact execution or further semantic tightening.
"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.audit_extreme_weapon_damage_same_build_resource_tightening as tightening
import tools.audit_extreme_weapon_damage_reduced_physical_upper_bound as reduced


_RESOURCE_OBJECTIVES = ("max_magicka", "max_stamina")
_ARMOR_BASE_WARNING = re.compile(
    r"^(Head|Shoulders|Chest|Hands|Waist|Legs|Feet) armor base: "
    r"CP160 Gold required \(level unset, quality unset\)$"
)
_WEAPON_BASE_WARNING = re.compile(
    r"^(Front Bar|Back Bar) weapon base: "
    r"CP160 Gold required \(level unset, quality unset\)$"
)

# Reviewed U50 sheet-power ceilings for the recurring survivors.
_DREUGH_STATIC = 129.0 + 129.0
_DREUGH_NAMED_POWER_PERCENT = 0.20
_NIX_STATIC = 129.0 * 3.0
_SPC_STATIC = 129.0
_DAGON_STATIC = 129.0 + 129.0


def _reconcile_resource_unresolved(
    objective_key: str,
    unresolved: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    objective = str(objective_key or "").strip().casefold()
    effective: list[str] = []
    neutralized: list[str] = []
    for raw in unresolved:
        message = str(raw or "").strip()
        if not message:
            continue
        metadata_only = (
            _ARMOR_BASE_WARNING.fullmatch(message)
            or _WEAPON_BASE_WARNING.fullmatch(message)
        )
        if objective in _RESOURCE_OBJECTIVES and metadata_only:
            neutralized.append(message)
            continue
        effective.append(message)
    return tuple(dict.fromkeys(effective)), tuple(dict.fromkeys(neutralized))


def _semantic_bound(joint, evidence):
    name = str(joint.set_name)
    count = int(joint.piece_count)

    if name == "Dreugh King Slayer" and count == 5:
        return reduced._BoundedBreakpoint(
            row=joint,
            flat=_DREUGH_STATIC,
            percent=_DREUGH_NAMED_POWER_PERCENT,
            assumptions=(
                "258 static sheet power; one 20% Major Brutality/Sorcery named-power ceiling",
            ),
        )

    if name == "Nix-Hound's Howl" and count == 5:
        return reduced._BoundedBreakpoint(
            row=joint,
            flat=_NIX_STATIC,
            percent=0.0,
            assumptions=(
                "Major Courage duplicates reviewed baseline; duration scaling is not Weapon Damage",
            ),
        )

    if name == "Spell Power Cure" and count == 5:
        return reduced._BoundedBreakpoint(
            row=joint,
            flat=_SPC_STATIC,
            percent=0.0,
            assumptions=("Major Courage duplicates reviewed baseline",),
        )

    if name == "Dagon's Dominion" and count == 5:
        return reduced._BoundedBreakpoint(
            row=joint,
            flat=_DAGON_STATIC,
            percent=0.0,
            assumptions=(
                "492 AoE-ability damage is scoped output and cannot raise sheet Weapon Damage",
            ),
        )

    return reduced._semantic_bound(joint, evidence)


def main() -> int:
    # tightening._bounded_frontier calls its imported audit-local _semantic_bound.
    tightening._semantic_bound = _semantic_bound
    tightening._reconcile_resource_unresolved = _reconcile_resource_unresolved

    print("EXTREME WEAPON DAMAGE KEY-SET SEMANTIC TIGHTENING")
    print("dreugh_king_slayer_flat_bound=258.000")
    print("dreugh_king_slayer_percent_bound=0.200000")
    print("nix_hounds_howl_flat_bound=387.000")
    print("spell_power_cure_flat_bound=129.000")
    print("dagons_dominion_flat_bound=258.000")
    print("major_courage_duplicate_with_nongear_baseline=True")
    print("dagon_aoe_bonus_counts_as_sheet_weapon_damage=False")
    print()
    return tightening.main()


if __name__ == "__main__":
    raise SystemExit(main())
