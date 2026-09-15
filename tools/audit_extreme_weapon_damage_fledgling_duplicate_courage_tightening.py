from __future__ import annotations

"""Remove Fledgling's Nest duplicate Minor Courage from Weapon Damage frontier.

The potion-active Weapon Damage baseline already contains reviewed Minor Courage.
Fledgling's Nest has no static Weapon/Spell Damage line; its 5-piece Weapon/Spell
Damage contribution is exclusively Minor Courage after leaving the Gryphon Nest.
Named buffs of the same name do not stack, so its incremental Weapon Damage value
for this proof is zero.

All other semantics are inherited from the Oakensoul-corrected potion-active proof.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.audit_extreme_weapon_damage_major_brutality_baseline as baseline
import tools.audit_extreme_weapon_damage_oakensoul_duplicate_buff_tightening as oak

FLEDGLINGS_NEST = "Fledgling's Nest"


def _semantic_bound(joint, evidence):
    name = str(joint.set_name)
    count = int(joint.piece_count)
    if name == FLEDGLINGS_NEST and count == 5:
        return baseline.scoped.reduced._BoundedBreakpoint(
            row=joint,
            flat=0.0,
            percent=0.0,
            exact_execution_required=False,
            assumptions=(
                "5pc grants Minor Courage only; Minor Courage duplicates reviewed non-gear baseline",
            ),
        )
    return oak._semantic_bound(joint, evidence)


def main() -> int:
    # baseline._bounded_frontier resolves through its imported scoped semantic hook.
    baseline.scoped._semantic_bound = _semantic_bound

    print("EXTREME WEAPON DAMAGE FLEDGLING DUPLICATE-COURAGE TIGHTENING")
    print("fledglings_nest_flat_bound=0.000")
    print("fledglings_nest_percent_bound=0.000000")
    print("fledglings_nest_minor_courage_duplicates_nongear_baseline=True")
    print()
    return baseline.main()


if __name__ == "__main__":
    raise SystemExit(main())
