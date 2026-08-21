#!/usr/bin/env python3
"""Audit the UESP equation sheet against the translated formula package.

Run from repository root:
    python minmax/formulas/equation_inventory_audit.py

This is intentionally an inventory check. It does not rewrite formulas,
infer missing equations, or correct anomalies in the UESP source.
"""
from __future__ import annotations
import ast
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "equations.py"

ALIASES = {
    "LAUnarmed": "calculate_la_melee",
    "LAOneHand": "calculate_la_melee",
    "LATwoHand": "calculate_la_melee",
    "LAWerewolf": "calculate_la_melee",
    "Health": "calculate_max_health",
    "Magicka": "calculate_max_magicka",
    "Stamina": "calculate_max_stamina",
    "HealthRegen": "calculate_health_recovery",
    "MagickaRegen": "calculate_magicka_recovery",
    "StaminaRegen": "calculate_stamina_recovery",
    "SpellDamage": "calculate_spell_damage",
    "WeaponDamage": "calculate_weapon_damage",
    "SpellCrit": "calculate_spell_critical",
    "SpellCritDamage": "calculate_spell_critical_damage",
    "WeaponCritDamage": "calculate_weapon_critical_damage",
    "SpellCritHealing": "calculate_spell_critical_healing",
    "WeaponCritHealing": "calculate_weapon_critical_healing",
    "SpellResist": "calculate_spell_resistance",
    "PhysicalResist": "calculate_physical_resistance",
    "SpellPenetration": "calculate_spell_penetration",
    "PhysicalPenetration": "calculate_physical_penetration",
    "EffectiveSpellPower": "calculate_effective_spell_power",
    "EffectiveWeaponPower": "calculate_effective_weapon_power",
    "EffectivePower": "calculate_effective_power",
    "StatusFlameSpellDamage": "calculate_status_spell_damage",
    "Bloodthirsty": "calculate_bloodthirsty",
}
SOURCE_ALIASES = {"X", "Overcharged", "Sundered", "Disease", "Poison"}

def canonical(name: str) -> str:
    return re.sub(r"_", "", name).lower()

def equations():
    result = []
    for line_no, line in enumerate(SOURCE.read_text(encoding="utf-8").splitlines(), 1):
        match = re.match(r"^([A-Za-z][A-Za-z0-9_]*)\s*=", line)
        if match:
            result.append((match.group(1), line_no))
    return result

def functions():
    result = {}
    for path in ROOT.glob("*.py"):
        if path.name == Path(__file__).name:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result[node.name] = path.name
    return result

def expected(equation: str) -> str:
    if equation in ALIASES:
        return ALIASES[equation]
    return "calculate_" + re.sub(r"(?<!^)(?=[A-Z])", "_", equation).lower()

def main() -> int:
    source_equations = equations()
    funcs = functions()
    canonical_funcs = {canonical(name): name for name in funcs}
    duplicates = Counter(name for name, _ in source_equations)
    missing = []
    seen = set()

    for name, line in source_equations:
        if name in SOURCE_ALIASES:
            continue
        target = expected(name)
        if target in funcs or canonical(target) in canonical_funcs:
            continue
        if name not in seen:
            missing.append((name, line, target))
            seen.add(name)

    print(f"Source equation occurrences : {len(source_equations)}")
    print(f"Unique equation names       : {len(duplicates)}")
    print(f"Formula functions found     : {len(funcs)}")
    print(f"Unique equations missing    : {len(missing)}")
    print()
    print("SOURCE DUPLICATES")
    for name, count in duplicates.items():
        if count > 1:
            lines = [str(line) for n, line in source_equations if n == name]
            print(f"  {name}: {count} occurrences (lines {', '.join(lines)})")
    print()
    print("MISSING")
    if missing:
        for name, line, target in missing:
            print(f"  {name} (source line {line}) -> {target}")
        return 2
    print("  none")
    print("\nSTATUS: COMPLETE INVENTORY")
    print("Source duplicates and explicit aliases remain visible above.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
