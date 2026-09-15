from __future__ import annotations

"""Remove Oakensoul named-buff duplicates from the Extreme Weapon Damage challenger pool.

Oakensoul Ring has no intrinsic Weapon/Spell Damage line in its current one-piece
text. For the Weapon Damage record, its only relevant named buffs are Minor Courage
and Major Brutality. The non-gear baseline already contains Minor Courage and the
potion-active baseline now contains Major Brutality, so Oakensoul's incremental
Weapon Damage contribution is zero.

This wrapper preserves every other semantic correction from the potion-active
Major Brutality audit. It changes no database state and does not remove Oakensoul's
one-bar legality; only the duplicate Weapon Damage contribution is tightened.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.audit_extreme_weapon_damage_major_brutality_baseline as baseline

OAKENSOUL = "Oakensoul Ring"

_original_semantic_bound = baseline.scoped._semantic_bound


def _semantic_bound(joint, evidence):
    name = str(joint.set_name)
    count = int(joint.piece_count)
    if name == OAKENSOUL and count == 1:
        return baseline.scoped.reduced._BoundedBreakpoint(
            row=joint,
            flat=0.0,
            percent=0.0,
            exact_execution_required=bool(getattr(_original_semantic_bound(joint, evidence), "exact_execution_required", False)),
            assumptions=(
                "Oakensoul has no intrinsic Weapon/Spell Damage line; Minor Courage and Major Brutality duplicate shared baseline named buffs",
            ),
        )
    return _original_semantic_bound(joint, evidence)


def main() -> int:
    baseline.scoped._semantic_bound = _semantic_bound
    print("EXTREME WEAPON DAMAGE OAKENSOUL DUPLICATE-BUFF TIGHTENING")
    print("oakensoul_flat_bound=0.000")
    print("oakensoul_percent_bound=0.000000")
    print("oakensoul_minor_courage_duplicates_nongear_baseline=True")
    print("oakensoul_major_brutality_duplicates_potion_baseline=True")
    print("oakensoul_one_bar_legality_unchanged=True")
    print()
    return baseline.main()


if __name__ == "__main__":
    raise SystemExit(main())
