from __future__ import annotations

"""Audit already-canonical U50 Weapon Damage power layers.

This is deliberately a denominator/inventory audit, not a final record claim. It
records the reusable power mechanics Extreme can already consume before we spend
any time on genuinely unresolved class, gear, trait, enchant, CP, or runtime
branches.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.combat_effect_semantics import GameUpdate
from minmax.named_combat_buffs import effects_for_buff
from minmax.passive_math import (
    FIGHTERS_GUILD_SLAYER_WEAPON_SPELL_DAMAGE_PERCENT_PER_SLOTTED,
    MEDIUM_ARMOR_WEAPON_SPELL_DAMAGE_PERCENT_PER_PIECE,
    fighters_guild_slayer_weapon_spell_damage_percent,
    medium_armor_weapon_spell_damage_percent,
)
from minmax.stat_ids import StatId
from services.extreme_arcanist_harnessed_quintessence_service import (
    ExtremeArcanistHarnessedQuintessenceService,
)
from services.extreme_skill_standing_effect_service import (
    ExtremeSkillStandingEffectService,
)


def _weapon_effect(name: str):
    rows = tuple(
        effect
        for effect in effects_for_buff(name, game_update=GameUpdate.U50)
        if effect.stat is StatId.WEAPON_DAMAGE
    )
    if len(rows) != 1:
        raise RuntimeError(f"Expected exactly one U50 Weapon Damage effect for {name!r}, got {rows!r}")
    return rows[0]


def main() -> int:
    minor_brutality = _weapon_effect("Minor Brutality")
    major_brutality = _weapon_effect("Major Brutality")
    minor_courage = _weapon_effect("Minor Courage")
    major_courage = _weapon_effect("Major Courage")

    medium_seven = medium_armor_weapon_spell_damage_percent(7)
    fighters_five_normal = fighters_guild_slayer_weapon_spell_damage_percent(5)
    fighters_six_with_ultimate = fighters_guild_slayer_weapon_spell_damage_percent(6)

    arcanist_rank_two = ExtremeArcanistHarnessedQuintessenceService.POWER_BY_RANK[2]
    arcanist_duration = ExtremeArcanistHarnessedQuintessenceService.DURATION_SECONDS

    inspiration = ExtremeSkillStandingEffectService.effects_for_skill(
        "Tome-Bearer's Inspiration",
        reference_value=1000.0,
    )
    inspiration_weapon = tuple(
        row for row in inspiration if row.objective_key == "weapon_damage"
    )

    unresolved: list[str] = []
    if minor_brutality.bucket != "percent" or abs(minor_brutality.value - 0.10) > 1e-12:
        unresolved.append("Minor Brutality U50 Weapon Damage semantics differ from reviewed +10%")
    if major_brutality.bucket != "percent" or abs(major_brutality.value - 0.20) > 1e-12:
        unresolved.append("Major Brutality U50 Weapon Damage semantics differ from reviewed +20%")
    if minor_courage.bucket != "flat" or abs(minor_courage.value - 215.0) > 1e-12:
        unresolved.append("Minor Courage U50 Weapon Damage semantics differ from reviewed +215")
    if major_courage.bucket != "flat" or abs(major_courage.value - 430.0) > 1e-12:
        unresolved.append("Major Courage U50 Weapon Damage semantics differ from reviewed +430")
    if abs(medium_seven - 0.14) > 1e-12:
        unresolved.append("Seven Medium Armor Weapon/Spell Damage scaling differs from reviewed +14%")
    if abs(fighters_five_normal - 0.15) > 1e-12:
        unresolved.append("Five Fighters Guild normal slots do not resolve to reviewed +15% Slayer")
    if abs(fighters_six_with_ultimate - 0.18) > 1e-12:
        unresolved.append("Five normal + Fighters Guild Ultimate does not resolve to reviewed +18% Slayer ceiling")
    if abs(float(arcanist_rank_two) - 284.0) > 1e-12 or abs(float(arcanist_duration) - 10.0) > 1e-12:
        unresolved.append("Harnessed Quintessence rank-two window differs from reviewed +284 for 10s")
    if len(inspiration_weapon) != 1 or abs(inspiration_weapon[0].projected_delta - 200.0) > 1e-12:
        unresolved.append("Tome-Bearer's Inspiration standing Major Brutality projection is not +20%")

    print("EXTREME WEAPON DAMAGE CANONICAL POWER SEMANTICS")
    print("game_update=U50")
    print()
    print("NAMED BUFFS")
    print(f"minor_brutality_percent={minor_brutality.value * 100.0:.3f}")
    print(f"major_brutality_percent={major_brutality.value * 100.0:.3f}")
    print(f"minor_courage_flat={minor_courage.value:.3f}")
    print(f"major_courage_flat={major_courage.value:.3f}")
    print()
    print("STANDING PERCENT SOURCES")
    print(f"medium_armor_percent_per_piece={MEDIUM_ARMOR_WEAPON_SPELL_DAMAGE_PERCENT_PER_PIECE * 100.0:.3f}")
    print(f"seven_medium_percent={medium_seven * 100.0:.3f}")
    print(f"fighters_guild_slayer_percent_per_slot={FIGHTERS_GUILD_SLAYER_WEAPON_SPELL_DAMAGE_PERCENT_PER_SLOTTED * 100.0:.3f}")
    print(f"fighters_guild_five_normal_percent={fighters_five_normal * 100.0:.3f}")
    print(f"fighters_guild_five_normal_plus_ultimate_percent={fighters_six_with_ultimate * 100.0:.3f}")
    print()
    print("SKILL / CLASS CONDITIONAL SOURCES")
    print("tome_bearers_inspiration_major_brutality_percent=20.000")
    print(f"harnessed_quintessence_rank_two_flat={float(arcanist_rank_two):.3f}")
    print(f"harnessed_quintessence_duration_seconds={float(arcanist_duration):.3f}")
    print()
    print("TOPOLOGY NOTES")
    print("normal_skill_slots=5")
    print("ultimate_slots=1")
    print("fighters_guild_six_slot_ceiling_requires_fighters_guild_ultimate=True")
    print("major_brutality_named_buff_stacking_key_must_not_double_with_skill_carrier=True")
    print()
    print("PROOF GATES")
    print(f"named_power_buffs_canonical={not any('Brutality' in row or 'Courage' in row for row in unresolved)}")
    print(f"medium_armor_power_semantics_canonical={not any('Medium Armor' in row for row in unresolved)}")
    print(f"fighters_guild_slayer_semantics_canonical={not any('Fighters Guild' in row or 'Slayer' in row for row in unresolved)}")
    print(f"harnessed_quintessence_semantics_canonical={not any('Harnessed Quintessence' in row for row in unresolved)}")
    carrier_closed = not any("Tome-Bearer's" in row for row in unresolved)
    print(f"skill_major_brutality_carrier_canonical={carrier_closed}")
    print(f"unresolved_count={len(unresolved)}")
    for row in unresolved:
        print(f"  unresolved: {row}")
    print(f"canonical_power_semantics_closed={not unresolved}")
    print("NEXT_STEP=combine this closed power-layer inventory with the foundation audit's omitted-axis report; then close only the surviving gear/trait/enchant/CP/runtime branches")
    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
