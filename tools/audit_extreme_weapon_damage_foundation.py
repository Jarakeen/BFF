from __future__ import annotations

"""Fast inventory audit for the Extreme Weapon Damage denominator.

This audit deliberately does NOT execute the full structural optimizer. Weapon
Damage currently has enough unclosed dynamic axes that a whole-universe scoring
pass is wasted work and can be very slow. Instead, this script inventories the
finite legality universe plus the objective-relevant canonical mechanic owners
that already exist. Follow-up audits close those axes independently and only then
compose a final exact search.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.named_combat_buffs import effects_for_buff
from minmax.passive_math import (
    FIGHTERS_GUILD_SLAYER_WEAPON_SPELL_DAMAGE_PERCENT_PER_SLOTTED,
    MEDIUM_ARMOR_WEAPON_SPELL_DAMAGE_PERCENT_PER_PIECE,
)
from minmax.stat_ids import StatId
from services.extreme_arcanist_harnessed_quintessence_service import (
    ExtremeArcanistHarnessedQuintessenceService,
)
from services.extreme_global_search_universe_service import (
    ExtremeGlobalSearchUniverseService,
)

OBJECTIVE = "weapon_damage"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _weapon_buff(name: str) -> tuple[float, str] | None:
    rows = tuple(
        row
        for row in effects_for_buff(name)
        if row.stat is StatId.WEAPON_DAMAGE
    )
    if len(rows) != 1:
        return None
    return float(rows[0].value), str(rows[0].bucket)


def main() -> int:
    database = Path(_parser().parse_args().database)
    universe = ExtremeGlobalSearchUniverseService(database).build()
    jewelry_glyphs = JewelryGlyphEffectRepository(database)
    jewelry_traits = JewelryTraitRepository(database)

    weapon_glyph = tuple(
        row
        for row in jewelry_glyphs.get_jewelry_glyph_effect_by_name(
            "Glyph of Increase Physical Harm",
            use_max_value=True,
        )
        if row.stat is StatId.WEAPON_DAMAGE
    )
    infused = jewelry_traits.get_infused_enchantment_percent("Gold")
    bloodthirsty = jewelry_traits.get_bloodthirsty_max_damage(
        quality="Gold",
        level="CP160",
    )

    owned_axes = {
        "structural legality universe": universe.structural_denominator_proven,
        "Minor Brutality": _weapon_buff("Minor Brutality") is not None,
        "Major Brutality": _weapon_buff("Major Brutality") is not None,
        "Minor Courage": _weapon_buff("Minor Courage") is not None,
        "Major Courage": _weapon_buff("Major Courage") is not None,
        "Medium Armor power passive": MEDIUM_ARMOR_WEAPON_SPELL_DAMAGE_PERCENT_PER_PIECE > 0.0,
        "Fighters Guild Slayer passive": FIGHTERS_GUILD_SLAYER_WEAPON_SPELL_DAMAGE_PERCENT_PER_SLOTTED > 0.0,
        "Weapon Damage jewelry glyph": len(weapon_glyph) == 1,
        "Gold Infused jewelry magnitude": infused is not None,
        "Gold Bloodthirsty ceiling": bloodthirsty is not None,
        "Harnessed Quintessence runtime power": (
            ExtremeArcanistHarnessedQuintessenceService.POWER_BY_RANK.get(2) == 284.0
        ),
    }

    unresolved = tuple(name for name, available in owned_axes.items() if not available)

    print("EXTREME WEAPON DAMAGE FAST FOUNDATION AUDIT")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print()
    print("STRUCTURAL UNIVERSE")
    print(f"race_count={len(universe.races)}")
    print(f"class_route_count={len(universe.class_routes)}")
    print(f"attribute_allocation_count={len(universe.attribute_allocations)}")
    print(f"active_bars={universe.active_bars!r}")
    print(f"structural_denominator_proven={universe.structural_denominator_proven}")
    print()
    print("CANONICAL OWNERS ALREADY AVAILABLE")
    for name, available in owned_axes.items():
        print(f"{name}={available}")
    print()
    print("DEFERRED DYNAMIC AXES")
    for axis in universe.deferred_dynamic_axes:
        print(f"  deferred: {axis}")
    print()
    print("FOUNDATION SUMMARY")
    print(f"owned_axis_count={sum(1 for value in owned_axes.values() if value)}")
    print(f"owner_gap_count={len(unresolved)}")
    for row in unresolved:
        print(f"  unresolved_owner: {row}")
    print(f"foundation_inventory_closed={not unresolved and universe.structural_denominator_proven}")
    print("weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=use the focused power-semantics and jewelry-frontier audits; then close weapon trait/enchant, named gear, CP, class/passive, and runtime-state axes before any final whole-build search"
    )
    return 0 if not unresolved and universe.structural_denominator_proven else 2


if __name__ == "__main__":
    raise SystemExit(main())
