from __future__ import annotations

"""Audit whether closed Weapon Damage proof axes can be reused for Spell Damage.

This is intentionally a parity/foundation audit, not a final Spell Damage record.
It verifies objective-specific mirrors through their canonical owners instead of
assuming ESO hybridization makes every Weapon/Spell Damage path identical.

The audit compares:
* race contribution winner;
* U50 Mundus winner and magnitude;
* jewelry glyph magnitude;
* Minor/Major named power buffs;
* shared Courage buffs;
* Extreme potion profile;
* Expert Mage objective support.

Any mismatch remains an explicit Spell Damage proof obligation.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.named_combat_buffs import effects_for_buff
from minmax.race_repository import RaceRepository
from minmax.stat_ids import StatId
from services.extreme_blueprint_service import ExtremeBlueprintService
from services.extreme_mundus_objective_service import ExtremeMundusObjectiveService
from services.extreme_race_objective_service import ExtremeRaceObjectiveService
from services.extreme_subclass_slot_allocation_service import ExtremeSubclassSlotAllocationService
from tools.audit_extreme_weapon_damage_sorcerer_free_resource_witness import _pure_sorcerer_route

DATABASE = Path(get_data_dir()) / "eso.db"


def _buff(name: str, stat: StatId):
    rows = tuple(row for row in effects_for_buff(name) if row.stat is stat)
    if len(rows) != 1:
        return None
    row = rows[0]
    return float(row.value), str(row.bucket)


def _glyph_value(repository: JewelryGlyphEffectRepository, name: str, stat: StatId):
    rows = tuple(
        row
        for row in repository.get_jewelry_glyph_effect_by_name(name, use_max_value=True)
        if row.stat is stat
    )
    if len(rows) != 1:
        return None
    return float(rows[0].value)


def main() -> int:
    race_repository = RaceRepository(DATABASE)
    mundus_repository = MundusRepository(DATABASE, game_update=U50_GAME_UPDATE)
    glyph_repository = JewelryGlyphEffectRepository(DATABASE)

    weapon_race = ExtremeRaceObjectiveService.best_for_objective(race_repository, "weapon_damage")
    spell_race = ExtremeRaceObjectiveService.best_for_objective(race_repository, "spell_damage")
    weapon_mundus = ExtremeMundusObjectiveService.best_for_objective(mundus_repository, "weapon_damage")
    spell_mundus = ExtremeMundusObjectiveService.best_for_objective(mundus_repository, "spell_damage")

    weapon_glyph = _glyph_value(
        glyph_repository,
        "Glyph of Increase Physical Harm",
        StatId.WEAPON_DAMAGE,
    )
    spell_glyph = _glyph_value(
        glyph_repository,
        "Glyph of Increase Magical Harm",
        StatId.SPELL_DAMAGE,
    )

    weapon_minor = _buff("Minor Brutality", StatId.WEAPON_DAMAGE)
    spell_minor = _buff("Minor Sorcery", StatId.SPELL_DAMAGE)
    weapon_major = _buff("Major Brutality", StatId.WEAPON_DAMAGE)
    spell_major = _buff("Major Sorcery", StatId.SPELL_DAMAGE)
    weapon_minor_courage = _buff("Minor Courage", StatId.WEAPON_DAMAGE)
    spell_minor_courage = _buff("Minor Courage", StatId.SPELL_DAMAGE)
    weapon_major_courage = _buff("Major Courage", StatId.WEAPON_DAMAGE)
    spell_major_courage = _buff("Major Courage", StatId.SPELL_DAMAGE)

    route = _pure_sorcerer_route()
    weapon_expert = ExtremeSubclassSlotAllocationService.best_allocation(
        tuple(route.equipped_skill_lines),
        "weapon_damage",
        reference_value=0.0,
    )
    spell_expert = ExtremeSubclassSlotAllocationService.best_allocation(
        tuple(route.equipped_skill_lines),
        "spell_damage",
        reference_value=0.0,
    )

    # The blueprint owns the canonical self-usable potion profile.
    blueprint = ExtremeBlueprintService(database_path=DATABASE)
    weapon_objective = blueprint.extreme.objective("weapon_damage")
    spell_objective = blueprint.extreme.objective("spell_damage")
    weapon_potion = blueprint._potion_profile(weapon_objective)
    spell_potion = blueprint._potion_profile(spell_objective)

    checks = {
        "race_winner_present": weapon_race is not None and spell_race is not None,
        "race_delta_mirrors": (
            weapon_race is not None
            and spell_race is not None
            and abs(float(weapon_race.projected_delta) - float(spell_race.projected_delta)) <= 1e-9
        ),
        "mundus_winner_present": weapon_mundus is not None and spell_mundus is not None,
        "mundus_delta_mirrors": (
            weapon_mundus is not None
            and spell_mundus is not None
            and abs(float(weapon_mundus.projected_delta) - float(spell_mundus.projected_delta)) <= 1e-9
        ),
        "jewelry_glyph_mirrors": (
            weapon_glyph is not None
            and spell_glyph is not None
            and abs(weapon_glyph - spell_glyph) <= 1e-9
        ),
        "minor_power_buff_mirrors": weapon_minor == spell_minor,
        "major_power_buff_mirrors": weapon_major == spell_major,
        "minor_courage_mirrors": weapon_minor_courage == spell_minor_courage,
        "major_courage_mirrors": weapon_major_courage == spell_major_courage,
        "expert_mage_mirrors": (
            weapon_expert is not None
            and spell_expert is not None
            and abs(float(weapon_expert.projected_delta) - float(spell_expert.projected_delta)) <= 1e-9
        ),
        "weapon_power_potion_is_major_brutality": weapon_potion == ("Weapon Power potion", "Major Brutality"),
        "spell_power_potion_is_major_sorcery": spell_potion == ("Spell Power potion", "Major Sorcery"),
    }

    unresolved = tuple(name for name, passed in checks.items() if not passed)

    print("EXTREME SPELL DAMAGE FOUNDATION PARITY")
    print(f"database={DATABASE}")
    print()
    print("RACE")
    print(
        f"weapon={None if weapon_race is None else (weapon_race.race_name, float(weapon_race.projected_delta))!r}"
    )
    print(
        f"spell={None if spell_race is None else (spell_race.race_name, float(spell_race.projected_delta))!r}"
    )
    print()
    print("MUNDUS")
    print(
        f"weapon={None if weapon_mundus is None else (weapon_mundus.mundus_name, float(weapon_mundus.projected_delta))!r}"
    )
    print(
        f"spell={None if spell_mundus is None else (spell_mundus.mundus_name, float(spell_mundus.projected_delta))!r}"
    )
    print()
    print("JEWELRY GLYPH")
    print(f"weapon_physical_harm={weapon_glyph!r}")
    print(f"spell_magical_harm={spell_glyph!r}")
    print()
    print("NAMED BUFFS")
    print(f"minor_brutality={weapon_minor!r}")
    print(f"minor_sorcery={spell_minor!r}")
    print(f"major_brutality={weapon_major!r}")
    print(f"major_sorcery={spell_major!r}")
    print(f"weapon_minor_courage={weapon_minor_courage!r}")
    print(f"spell_minor_courage={spell_minor_courage!r}")
    print(f"weapon_major_courage={weapon_major_courage!r}")
    print(f"spell_major_courage={spell_major_courage!r}")
    print()
    print("SORCERER / POTION")
    print(f"weapon_expert_mage={None if weapon_expert is None else float(weapon_expert.projected_delta):!r}")
    print(f"spell_expert_mage={None if spell_expert is None else float(spell_expert.projected_delta):!r}")
    print(f"weapon_potion={weapon_potion!r}")
    print(f"spell_potion={spell_potion!r}")
    print()
    print("PARITY CHECKS")
    for name, passed in checks.items():
        print(f"{name}={passed}")
    print()
    print("PROOF STATUS")
    print(f"parity_check_count={len(checks)}")
    print(f"parity_gap_count={len(unresolved)}")
    for name in unresolved:
        print(f"  unresolved: {name}")
    print(f"spell_damage_foundation_parity_ready={not unresolved}")
    print("final_spell_damage_record_closed=False")
    print(
        "NEXT_STEP=if parity is green, reuse the closed Weapon Damage physical/conditional proof skeleton with spell-specific objective IDs, The Apprentice, Magical Harm, and Major Sorcery; independently replay the 79-witness denominator before claiming the Spell Damage record"
    )
    return 0 if not unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
