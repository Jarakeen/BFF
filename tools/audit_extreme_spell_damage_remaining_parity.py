from __future__ import annotations

"""Audit remaining Weapon/Spell Damage proof parity before denominator reuse.

Foundation parity already proved race, Mundus magnitude, jewelry glyph magnitude,
named power buffs, Courage, Expert Mage, and potion profile symmetry.  This audit
closes the remaining reusable axes needed before replaying the closed 79-witness
Weapon Damage denominator for Spell Damage:

* Champion Point flat-power loadout ceiling;
* ordinary weapon enchant power, whose canonical effect type is paired
  ``weapon_spell_damage``;
* full named-gear breakpoint relevance/status parity between weapon_damage and
  spell_damage over the same canonical set breakpoint denominator.

It does not claim the final Spell Damage record.  Any catalog mismatch remains an
explicit independent Spell Damage proof obligation.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.gear_set_repository import GearSetRepository
from minmax.rule_repository import RuleRepository
from minmax.weapon_enchantment_effect_service import WeaponEnchantmentEffectService
from minmax.weapon_enchantment_repository import WeaponEnchantmentRepository
from services.champion_point_loadout_service import ChampionPointLoadoutCandidate, ChampionPointLoadoutService
from services.extreme_champion_point_objective_service import ExtremeChampionPointObjectiveService
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService

DATABASE = ROOT / "data" / "eso.db"


def _cp_ceiling(objective: str) -> float:
    repository = ChampionPointStaticRepository(DATABASE)
    candidates: list[ChampionPointLoadoutCandidate] = []
    for record in repository.slottable_records():
        projected = ExtremeChampionPointObjectiveService.candidate_for_record(
            repository,
            record,
            objective,
            reference_value=0.0,
        )
        if projected.reviewed_delta is not None and projected.reviewed_delta > 0.0:
            candidates.append(
                ChampionPointLoadoutCandidate(
                    name=record.name,
                    discipline_index=record.discipline_index,
                    flat_ceiling=float(projected.reviewed_delta),
                    condition=None,
                )
            )
    return float(ChampionPointLoadoutService.build(tuple(candidates)).total_flat_ceiling)


def _weapon_enchant_ceiling() -> tuple[float, int]:
    repository = WeaponEnchantmentRepository(DATABASE)
    service = WeaponEnchantmentEffectService(repository, RuleRepository(DATABASE))
    values = []
    for item_id, _name in repository.list_items():
        for effect in service.resolve_effects(item_id):
            if str(effect.effect_type or "").strip().casefold() == "weapon_spell_damage":
                values.append(float(effect.value))
    return (max(values, default=0.0), len(values))


def _status(row) -> str:
    return str(getattr(row.status, "value", row.status))


def _catalog_map(catalog):
    return {
        (int(row.set_id), int(row.piece_count)): row
        for row in catalog.evidence
    }


def main() -> int:
    weapon_cp = _cp_ceiling("weapon_damage")
    spell_cp = _cp_ceiling("spell_damage")
    enchant, enchant_rows = _weapon_enchant_ceiling()

    repository = GearSetRepository(DATABASE)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository)
    weapon_catalog = relevance.build("weapon_damage", breakpoints)
    spell_catalog = relevance.build("spell_damage", breakpoints)
    weapon_map = _catalog_map(weapon_catalog)
    spell_map = _catalog_map(spell_catalog)
    keys = tuple(sorted(set(weapon_map) | set(spell_map)))

    missing_weapon = []
    missing_spell = []
    delta_mismatch = []
    status_mismatch = []
    unresolved_shape_mismatch = []

    for key in keys:
        weapon = weapon_map.get(key)
        spell = spell_map.get(key)
        if weapon is None:
            missing_weapon.append(key)
            continue
        if spell is None:
            missing_spell.append(key)
            continue
        if abs(float(weapon.reviewed_delta) - float(spell.reviewed_delta)) > 1e-9:
            delta_mismatch.append(
                (key, weapon.set_name, float(weapon.reviewed_delta), float(spell.reviewed_delta))
            )
        if _status(weapon) != _status(spell):
            status_mismatch.append((key, weapon.set_name, _status(weapon), _status(spell)))
        weapon_unresolved = tuple(str(x) for x in (weapon.candidate.unresolved or ()))
        spell_unresolved = tuple(str(x) for x in (spell.candidate.unresolved or ()))
        if bool(weapon_unresolved) != bool(spell_unresolved):
            unresolved_shape_mismatch.append(
                (key, weapon.set_name, bool(weapon_unresolved), bool(spell_unresolved))
            )

    checks = {
        "cp_flat_ceiling_mirrors": abs(weapon_cp - spell_cp) <= 1e-9,
        "paired_weapon_spell_enchant_present": enchant > 0.0 and enchant_rows > 0,
        "named_gear_key_denominator_mirrors": not missing_weapon and not missing_spell,
        "named_gear_reviewed_delta_mirrors": not delta_mismatch,
        "named_gear_status_mirrors": not status_mismatch,
        "named_gear_unresolved_shape_mirrors": not unresolved_shape_mismatch,
    }
    unresolved = tuple(name for name, passed in checks.items() if not passed)

    print("EXTREME SPELL DAMAGE REMAINING PARITY")
    print(f"database={DATABASE}")
    print()
    print("CHAMPION POINT")
    print(f"weapon_flat_ceiling={weapon_cp:.3f}")
    print(f"spell_flat_ceiling={spell_cp:.3f}")
    print()
    print("WEAPON ENCHANT")
    print("canonical_effect_type='weapon_spell_damage'")
    print(f"matching_effect_rows={enchant_rows}")
    print(f"best_flat_power={enchant:.3f}")
    print()
    print("NAMED GEAR CATALOG PARITY")
    print(f"breakpoint_sets={len(breakpoints.sets)}")
    print(f"weapon_relevance_rows={len(weapon_catalog.evidence)}")
    print(f"spell_relevance_rows={len(spell_catalog.evidence)}")
    print(f"missing_weapon_rows={len(missing_weapon)}")
    print(f"missing_spell_rows={len(missing_spell)}")
    print(f"delta_mismatch_rows={len(delta_mismatch)}")
    print(f"status_mismatch_rows={len(status_mismatch)}")
    print(f"unresolved_shape_mismatch_rows={len(unresolved_shape_mismatch)}")

    for label, rows in (
        ("delta_mismatch", delta_mismatch),
        ("status_mismatch", status_mismatch),
        ("unresolved_shape_mismatch", unresolved_shape_mismatch),
    ):
        for row in rows[:20]:
            print(f"  {label}: {row!r}")
        if len(rows) > 20:
            print(f"  {label}: ... {len(rows) - 20} additional rows omitted")
    print()

    print("PARITY CHECKS")
    for name, passed in checks.items():
        print(f"{name}={passed}")
    print()
    print("PROOF STATUS")
    print(f"remaining_parity_gap_count={len(unresolved)}")
    for name in unresolved:
        print(f"  unresolved: {name}")
    ready = not unresolved
    print(f"spell_damage_remaining_parity_ready={ready}")
    print("final_spell_damage_record_closed=False")
    print(
        "NEXT_STEP=if remaining parity is green, replay the closed 79-witness physical denominator "
        "with spell_damage, The Apprentice, Magical Harm, Major Sorcery, and the same reviewed "
        "conditional-set semantics before promoting any Spell Damage winner"
    )
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
