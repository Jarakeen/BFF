from __future__ import annotations

"""Conservative whole-build preweapon flat ceiling for Extreme Weapon Damage.

This audit is intentionally generous to the One Hand and Shield challenger.  It
adds mutually exclusive class/runtime maxima together, keeps both Courage flats,
uses the Bloodthirsty jewelry ceiling, and takes the strongest reviewed legal
named-gear package.  If even that over-counted nonweapon flat ceiling remains
below the zero-common-percent Sword-and-Board threshold, the +3% Sword and Board
passive cannot overtake the corrected Dual Wield weapon realization.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.gear_set_repository import GearSetRepository
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.named_combat_buffs import effects_for_buff
from minmax.race_repository import RaceRepository
from minmax.rule_repository import RuleRepository
from minmax.stat_ids import StatId
from minmax.weapon_enchantment_effect_service import WeaponEnchantmentEffectService
from minmax.weapon_enchantment_repository import WeaponEnchantmentRepository
from minmax.combat_effect_semantics import GameUpdate
from services.champion_point_loadout_service import ChampionPointLoadoutCandidate, ChampionPointLoadoutService
from services.extreme_armor_mundus_joint_objective_service import ExtremeArmorMundusJointObjectiveService
from services.extreme_arcanist_harnessed_quintessence_service import ExtremeArcanistHarnessedQuintessenceService
from services.extreme_blueprint_service import _SORCERER_EXPERT_MAGE_PER_SLOT
from services.extreme_champion_point_objective_service import ExtremeChampionPointObjectiveService
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_nightblade_class_mastery_healing_service import ExtremeNightbladeClassMasteryHealingService
from services.extreme_objective_named_gear_set_catalog_realization_service import ExtremeObjectiveNamedGearSetCatalogRealizationService
from services.extreme_race_objective_service import ExtremeRaceObjectiveService

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "weapon_damage"
SWORD_BOARD_THRESHOLD = 14113.333
BASE_LEVEL_50_POWER = 1000.0
JEWELRY_SLOTS = 3
GLYPH_NAME = "Glyph of Increase Physical Harm"


def _best_named_gear() -> tuple[float, tuple[tuple[str, int], ...], bool, tuple[str, ...]]:
    repository = GearSetRepository(DATABASE)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(DATABASE).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    realization = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    ).build(topology)
    evidence = {(int(row.set_id), int(row.piece_count)): row for row in relevance.evidence}
    best = 0.0
    signature: tuple[tuple[str, int], ...] = ()
    missing: list[str] = []
    for topology_row in realization.realization.topologies:
        for witness in topology_row.realizations:
            score = 0.0
            parts: list[tuple[str, int]] = []
            for set_id, set_name, count in zip(witness.set_ids, witness.set_names, witness.counts, strict=True):
                row = evidence.get((int(set_id), int(count)))
                if row is None:
                    missing.append(f"missing named-gear evidence: {set_name} {count}pc")
                    continue
                score += max(0.0, float(row.reviewed_delta))
                parts.append((str(set_name), int(count)))
            candidate = tuple(parts)
            if score > best + 1e-9 or (abs(score - best) <= 1e-9 and candidate < signature):
                best = score
                signature = candidate
    unresolved = tuple(dict.fromkeys((*relevance.unresolved, *realization.unresolved, *missing)))
    closed = relevance.denominator_proven and realization.denominator_proven and not unresolved
    return best, signature, closed, unresolved


def _race_ceiling() -> tuple[str, float]:
    row = ExtremeRaceObjectiveService.best_for_objective(RaceRepository(DATABASE), OBJECTIVE)
    return ("<none>", 0.0) if row is None else (row.race_name, float(row.projected_delta))


def _jewelry_ceiling() -> float:
    glyphs = JewelryGlyphEffectRepository(DATABASE)
    traits = JewelryTraitRepository(DATABASE)
    rows = tuple(
        effect for effect in glyphs.get_jewelry_glyph_effect_by_name(GLYPH_NAME, use_max_value=True)
        if effect.stat is StatId.WEAPON_DAMAGE
    )
    glyph = max((float(row.value) for row in rows), default=0.0)
    bloodthirsty = traits.get_bloodthirsty_max_damage(quality="Gold", level="CP160") or 0.0
    return JEWELRY_SLOTS * (glyph + float(bloodthirsty))


def _mundus_ceiling() -> float:
    repository = MundusRepository(DATABASE, game_update=U50_GAME_UPDATE)
    row = ExtremeArmorMundusJointObjectiveService.best_for_objective(repository, OBJECTIVE, reference_value=0.0)
    return 0.0 if row is None else float(row.mundus_delta)


def _cp_ceiling() -> float:
    repository = ChampionPointStaticRepository(DATABASE)
    candidates: list[ChampionPointLoadoutCandidate] = []
    for record in repository.slottable_records():
        projected = ExtremeChampionPointObjectiveService.candidate_for_record(repository, record, OBJECTIVE, reference_value=0.0)
        if projected.reviewed_delta is not None and projected.reviewed_delta > 0.0:
            candidates.append(ChampionPointLoadoutCandidate(
                name=record.name,
                discipline_index=record.discipline_index,
                flat_ceiling=float(projected.reviewed_delta),
                condition=None,
            ))
    return float(ChampionPointLoadoutService.build(tuple(candidates)).total_flat_ceiling)


def _courage_ceiling() -> float:
    total = 0.0
    for buff in ("Minor Courage", "Major Courage"):
        for effect in effects_for_buff(buff, game_update=GameUpdate.U50):
            if effect.stat is StatId.WEAPON_DAMAGE and effect.bucket == "flat":
                total += float(effect.value)
    return total


def _weapon_enchant_ceiling() -> float:
    repository = WeaponEnchantmentRepository(DATABASE)
    service = WeaponEnchantmentEffectService(repository, RuleRepository(DATABASE))
    best = 0.0
    for item_id, _name in repository.list_items():
        for effect in service.resolve_effects(item_id):
            if str(effect.effect_type or "").strip().casefold() == "weapon_spell_damage":
                best = max(best, float(effect.value))
    return best


def main() -> int:
    named_gear, named_signature, named_closed, named_unresolved = _best_named_gear()
    race_name, race = _race_ceiling()
    jewelry = _jewelry_ceiling()
    mundus = _mundus_ceiling()
    cp = _cp_ceiling()
    courage = _courage_ceiling()
    enchant = _weapon_enchant_ceiling()

    # Deliberate over-count: these maxima are mutually exclusive class routes.
    # Summing them is conservative for killing Sword-and-Board as a challenger.
    expert_mage = 6.0 * float(_SORCERER_EXPERT_MAGE_PER_SLOT)
    harnessed = max(ExtremeArcanistHarnessedQuintessenceService.POWER_BY_RANK.values())
    eye = float(ExtremeNightbladeClassMasteryHealingService.EYE_FOR_EXPLOITATION_MAX_POWER)
    class_runtime_overcount = expert_mage + harnessed + eye

    total = (
        BASE_LEVEL_50_POWER
        + race
        + jewelry
        + mundus
        + cp
        + courage
        + enchant
        + named_gear
        + class_runtime_overcount
    )
    headroom = SWORD_BOARD_THRESHOLD - total
    threshold_dominated = total < SWORD_BOARD_THRESHOLD - 1e-9

    print("EXTREME WEAPON DAMAGE PREWEAPON FLAT UPPER BOUND")
    print(f"database={DATABASE}")
    print()
    print("CLOSED / CONSERVATIVE FLAT SOURCES")
    print(f"base_level_50_power={BASE_LEVEL_50_POWER:.3f}")
    print(f"race={race_name!r} race_flat={race:.3f}")
    print(f"bloodthirsty_plus_glyph_jewelry={jewelry:.3f}")
    print(f"warrior_divines_mundus={mundus:.3f}")
    print(f"cp_flat={cp:.3f}")
    print(f"minor_plus_major_courage={courage:.3f}")
    print(f"ordinary_weapon_damage_enchant={enchant:.3f}")
    print(f"best_named_gear_reviewed_flat_delta={named_gear:.3f}")
    print(f"best_named_gear_signature={named_signature!r}")
    print()
    print("DELIBERATELY OVER-COUNTED MUTUALLY EXCLUSIVE CLASS/RUNTIME FLATS")
    print(f"sorcerer_expert_mage_six_slots={expert_mage:.3f}")
    print(f"arcanist_harnessed_quintessence={harnessed:.3f}")
    print(f"nightblade_eye_for_exploitation={eye:.3f}")
    print(f"class_runtime_overcount_total={class_runtime_overcount:.3f}")
    print("mutually_exclusive_class_routes_summed_on_purpose=True")
    print()
    print("SWORD AND BOARD DOMINANCE")
    print(f"conservative_preweapon_flat_upper_bound={total:.3f}")
    print(f" sword_board_threshold={SWORD_BOARD_THRESHOLD:.3f}")
    print(f"threshold_headroom={headroom:.3f}")
    print(f"sword_board_threshold_dominated={threshold_dominated}")
    print("common_percent_assumed_zero=True")
    print("positive_common_percent_only_makes_sword_board_harder_to_win=True")
    print()
    print("PROOF GATES")
    print(f"named_gear_denominator_closed={named_closed}")
    print(f"named_gear_unresolved_count={len(named_unresolved)}")
    for row in named_unresolved:
        print(f"  unresolved: {row}")
    closed = named_closed and threshold_dominated
    print(f"weapon_damage_preweapon_upper_bound_closed={closed}")
    print(f"dual_wield_weapon_champion_proven={closed}")
    print("NEXT_STEP=with weapon topology closed, compose the exact legal class/runtime and named-gear winner instead of the conservative over-count, then produce the final Weapon Damage record snapshot")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
