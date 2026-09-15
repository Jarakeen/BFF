from __future__ import annotations

"""Audit the preserved Lightning Staff light-attack formula contract.

This tool does not rewrite combat math and does not claim current ESO semantics.
It compares the architectural dependency contract for ``shock_staff`` against the
other preserved light-attack contracts so research can focus on the exact modifier
buckets that make Rotation Builder refuse Lightning Staff LA damage today.
"""

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.formulas.light_attack_contracts import LIGHT_ATTACK_CONTRACTS


_REFERENCE_LIGHT_ATTACKS = ("flame_staff", "frost_staff", "bow")
_SUSPICIOUS_SHOCK_INPUTS = (
    "skill_ha_damage",
    "set_ha_damage",
    "buff_empower",
    "dot_damage_done",
)
_EXPECTED_LA_FAMILY_INPUTS = (
    "skill_la_damage",
    "set_la_damage",
    "direct_damage_done",
)


@dataclass(frozen=True)
class LightningStaffLightAttackFormulaAudit:
    shock_inputs: tuple[str, ...]
    suspicious_heavy_or_dot_inputs: tuple[str, ...]
    missing_common_la_inputs: tuple[str, ...]
    reference_common_inputs: tuple[str, ...]

    @property
    def requires_source_review(self) -> bool:
        return bool(self.suspicious_heavy_or_dot_inputs or self.missing_common_la_inputs)


def audit_lightning_staff_light_attack_formula() -> LightningStaffLightAttackFormulaAudit:
    shock = LIGHT_ATTACK_CONTRACTS["shock_staff"]["inputs"]
    shock_inputs = tuple(shock)

    reference_sets = [
        set(LIGHT_ATTACK_CONTRACTS[name]["inputs"])
        for name in _REFERENCE_LIGHT_ATTACKS
    ]
    common = set.intersection(*reference_sets)

    suspicious = tuple(
        name for name in _SUSPICIOUS_SHOCK_INPUTS if name in shock
    )
    missing = tuple(
        name
        for name in _EXPECTED_LA_FAMILY_INPUTS
        if name in common and name not in shock
    )

    return LightningStaffLightAttackFormulaAudit(
        shock_inputs=shock_inputs,
        suspicious_heavy_or_dot_inputs=suspicious,
        missing_common_la_inputs=missing,
        reference_common_inputs=tuple(sorted(common)),
    )


def main() -> int:
    audit = audit_lightning_staff_light_attack_formula()

    print("============================================")
    print(" LIGHTNING STAFF LIGHT-ATTACK FORMULA AUDIT")
    print("============================================")
    print()
    print("Preserved shock-LA inputs:")
    for name in audit.shock_inputs:
        print(f"  - {name}")

    print()
    print("Heavy/Empower/DoT-shaped inputs requiring source review:")
    if audit.suspicious_heavy_or_dot_inputs:
        for name in audit.suspicious_heavy_or_dot_inputs:
            print(f"  - {name}")
    else:
        print("  - none")

    print()
    print("Common LA-family inputs absent from shock-LA contract:")
    if audit.missing_common_la_inputs:
        for name in audit.missing_common_la_inputs:
            print(f"  - {name}")
    else:
        print("  - none")

    print()
    if audit.requires_source_review:
        print(
            "Result: SOURCE REVIEW REQUIRED — keep Lightning Staff light-attack "
            "damage fail-closed until these contract differences are verified."
        )
    else:
        print("Result: no contract-level anomaly detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
