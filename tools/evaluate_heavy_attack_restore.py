from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.heavy_attack_restoration import (
    HeavyAttackWeaponType,
    resource_for_heavy_attack_weapon,
)


def _ratio(value: float, label: str) -> float:
    number = float(value)
    if number < 0:
        raise ValueError(f"{label} cannot be negative: {value}")
    return number


def infer_base_restore(
    *,
    observed_restore: int,
    cp_percent: float = 0.0,
    skill_percent: float = 0.0,
    set_percent: float = 0.0,
    buff_percent: float = 0.0,
    weapon_specific_percent: float = 0.0,
) -> float:
    observed = int(observed_restore)
    if observed < 0:
        raise ValueError(f"Observed restore cannot be negative: {observed_restore}")

    cp = _ratio(cp_percent, "CP percent")
    skill = _ratio(skill_percent, "Skill percent")
    set_value = _ratio(set_percent, "Set percent")
    buff = _ratio(buff_percent, "Buff percent")
    weapon_specific = _ratio(weapon_specific_percent, "Weapon-specific percent")

    multiplier = (1.0 + cp) * (1.0 + skill + set_value + buff) * (1.0 + weapon_specific)
    if multiplier <= 0:
        raise ValueError("Heavy-attack restore multiplier must be positive")
    return observed / multiplier


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Back-solve a current live ESO heavy-attack base resource restore from an observed gain"
    )
    parser.add_argument("--weapon", required=True, choices=[item.value for item in HeavyAttackWeaponType])
    parser.add_argument("--observed-restore", required=True, type=int)
    parser.add_argument("--cp-percent", type=float, default=0.0)
    parser.add_argument("--skill-percent", type=float, default=0.0)
    parser.add_argument("--set-percent", type=float, default=0.0)
    parser.add_argument("--buff-percent", type=float, default=0.0)
    parser.add_argument("--weapon-specific-percent", type=float, default=0.0)
    args = parser.parse_args()

    weapon = HeavyAttackWeaponType(args.weapon)
    resource = resource_for_heavy_attack_weapon(weapon)
    inferred = infer_base_restore(
        observed_restore=args.observed_restore,
        cp_percent=args.cp_percent,
        skill_percent=args.skill_percent,
        set_percent=args.set_percent,
        buff_percent=args.buff_percent,
        weapon_specific_percent=args.weapon_specific_percent,
    )

    print("=" * 48)
    print(" PHASE 4 LIVE HEAVY ATTACK RESTORE PROBE")
    print("=" * 48)
    print(f"Weapon:         {weapon.value}")
    print(f"Resource:       {resource.value}")
    print(f"Observed:       {args.observed_restore}")
    print(f"CP modifier:    {args.cp_percent:g}")
    print(f"Skill modifier: {args.skill_percent:g}")
    print(f"Set modifier:   {args.set_percent:g}")
    print(f"Buff modifier:  {args.buff_percent:g}")
    print(f"Weapon modifier:{args.weapon_specific_percent:g}")
    print()
    print(f"Inferred base:  {inferred:.6f}")
    print(f"Nearest int:    {round(inferred)}")
    print(f"Floor / ceil:   {math.floor(inferred)} / {math.ceil(inferred)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
