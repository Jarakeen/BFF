from __future__ import annotations

"""Remove ability-scoped power from the Extreme sheet/effective Weapon Damage axis.

The preceding key-set tightening corrected duplicate named buffs and several tooltip
parsing artifacts.  Its new survivor pool exposed a second repeated semantic family:
sets whose 5-piece bonus says that Weapon/Spell Damage is added only to a named
ability family or damage type.  Those bonuses can increase the damage coefficient
used by qualifying abilities, but they do not raise universal character-sheet Weapon
Damage and therefore must not be credited to this Extreme Weapon Damage record.

This wrapper keeps each set's ordinary static Weapon/Spell Damage line and zeroes only
the reviewed ability-scoped 5-piece contribution.  Target-conditioned generic power
such as Kvatch Gladiator is deliberately NOT changed here.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.audit_extreme_weapon_damage_key_set_semantic_tightening as key_tightening
import tools.audit_extreme_weapon_damage_same_build_resource_tightening as tightening
import tools.audit_extreme_weapon_damage_reduced_physical_upper_bound as reduced

# Reviewed static universal Weapon/Spell Damage retained after removing the scoped 5pc.
# Current U50 tooltips:
#   Spider Cultist Cowl: 4pc +129, 5pc +600 to Destruction Staff abilities.
#   Light Speaker: 4pc +129, 5pc +600 to Restoration Staff abilities.
#   War Maiden: 4pc +129, 5pc +600 to Magic Damage abilities.
#   Swamp Raider: 4pc +129, 5pc +600 to Poison/Disease abilities.
#   Sword-Singer: 3pc +129, 5pc +600 to Two Handed abilities.
#   Sword Dancer: 4pc +129, 5pc +600 to Dual Wield abilities.
#   Elemental Succession: 3pc +129, 5pc +492 only for the selected elemental type.
_ABILITY_SCOPED_STATIC = {
    "Spider Cultist Cowl": 129.0,
    "Light Speaker": 129.0,
    "War Maiden": 129.0,
    "Swamp Raider": 129.0,
    "Sword-Singer": 129.0,
    "Sword Dancer": 129.0,
    "Elemental Succession": 129.0,
}


def _semantic_bound(joint, evidence):
    name = str(joint.set_name)
    count = int(joint.piece_count)
    if count == 5 and name in _ABILITY_SCOPED_STATIC:
        return reduced._BoundedBreakpoint(
            row=joint,
            flat=float(_ABILITY_SCOPED_STATIC[name]),
            percent=0.0,
            assumptions=(
                "5pc Weapon/Spell Damage applies only to a qualifying ability family or damage type; excluded from universal Weapon Damage record",
            ),
        )
    return key_tightening._semantic_bound(joint, evidence)


def main() -> int:
    tightening._semantic_bound = _semantic_bound
    tightening._reconcile_resource_unresolved = key_tightening._reconcile_resource_unresolved

    print("EXTREME WEAPON DAMAGE ABILITY-SCOPED SET TIGHTENING")
    for name in sorted(_ABILITY_SCOPED_STATIC, key=str.casefold):
        print(f"{name.lower().replace(' ', '_').replace('-', '_').replace("'", '')}_flat_bound=129.000")
    print("ability_scoped_5pc_power_counts_as_universal_weapon_damage=False")
    print("target_conditioned_generic_power_unchanged=True")
    print()
    return tightening.main()


if __name__ == "__main__":
    raise SystemExit(main())
