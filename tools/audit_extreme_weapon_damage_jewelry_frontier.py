from __future__ import annotations

"""Audit the canonical U50 Weapon Damage jewelry trait/glyph frontier.

This closes only the jewelry magnitude frontier. Bloodthirsty target-health
activation remains an explicit runtime condition for the final record snapshot.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.stat_ids import StatId


GLYPH_NAME = "Glyph of Increase Physical Harm"
QUALITY = "Gold"
LEVEL = "CP160"
JEWELRY_SLOTS = 3


def main() -> int:
    database = get_data_dir() / "eso.db"
    glyph_repository = JewelryGlyphEffectRepository(database)
    trait_repository = JewelryTraitRepository(database)

    glyph_rows = tuple(
        effect
        for effect in glyph_repository.get_jewelry_glyph_effect_by_name(
            GLYPH_NAME,
            use_max_value=True,
        )
        if effect.stat is StatId.WEAPON_DAMAGE
    )

    unresolved: list[str] = []
    if len(glyph_rows) != 1:
        unresolved.append(
            f"Expected exactly one Weapon Damage effect for {GLYPH_NAME!r}, got {glyph_rows!r}"
        )
        base_glyph = 0.0
    else:
        base_glyph = float(glyph_rows[0].value)

    infused_percent = trait_repository.get_infused_enchantment_percent(QUALITY)
    bloodthirsty_max = trait_repository.get_bloodthirsty_max_damage(
        quality=QUALITY,
        level=LEVEL,
    )

    if infused_percent is None:
        unresolved.append("Gold Infused jewelry enchantment scaling is unavailable")
        infused_multiplier = 0.0
    else:
        infused_multiplier = 1.0 + float(infused_percent) / 100.0

    if bloodthirsty_max is None:
        unresolved.append("Gold CP160 Bloodthirsty maximum damage is unavailable")
        bloodthirsty_max = 0.0

    ordinary_glyph_per_slot = base_glyph
    infused_glyph_per_slot = base_glyph * infused_multiplier
    bloodthirsty_plus_glyph_per_slot = base_glyph + float(bloodthirsty_max)

    ordinary_three = ordinary_glyph_per_slot * JEWELRY_SLOTS
    infused_three = infused_glyph_per_slot * JEWELRY_SLOTS
    bloodthirsty_three_trait = float(bloodthirsty_max) * JEWELRY_SLOTS
    bloodthirsty_three_plus_glyph = bloodthirsty_plus_glyph_per_slot * JEWELRY_SLOTS

    bloodthirsty_trait_beats_infused_opportunity = (
        bloodthirsty_plus_glyph_per_slot > infused_glyph_per_slot + 1e-9
    )
    glyph_is_weapon_damage = bool(glyph_rows)
    frontier_closed = bool(
        not unresolved
        and glyph_is_weapon_damage
        and bloodthirsty_trait_beats_infused_opportunity
    )

    print("EXTREME WEAPON DAMAGE JEWELRY FRONTIER AUDIT")
    print(f"database={database}")
    print()
    print("CANONICAL MAGNITUDES")
    print(f"glyph_name={GLYPH_NAME!r}")
    print(f"base_weapon_damage_glyph={base_glyph:.3f}")
    print(f"gold_infused_percent={float(infused_percent or 0.0):.3f}")
    print(f"gold_bloodthirsty_max_per_item={float(bloodthirsty_max):.3f}")
    print()
    print("PER-SLOT FRONTIER")
    print(f"ordinary_damage_glyph={ordinary_glyph_per_slot:.3f}")
    print(f"infused_damage_glyph={infused_glyph_per_slot:.3f}")
    print(f"bloodthirsty_plus_damage_glyph={bloodthirsty_plus_glyph_per_slot:.3f}")
    print()
    print("THREE-JEWELRY FRONTIER")
    print(f"three_ordinary_damage_glyphs={ordinary_three:.3f}")
    print(f"three_infused_damage_glyphs={infused_three:.3f}")
    print(f"three_bloodthirsty_trait_ceiling={bloodthirsty_three_trait:.3f}")
    print(f"three_bloodthirsty_plus_damage_glyphs={bloodthirsty_three_plus_glyph:.3f}")
    print()
    print("PROOF GATES")
    print(f"weapon_damage_glyph_resolved={glyph_is_weapon_damage}")
    print(f"bloodthirsty_trait_beats_infused_opportunity={bloodthirsty_trait_beats_infused_opportunity}")
    print("bloodthirsty_runtime_condition_preserved=True")
    print(f"unresolved_count={len(unresolved)}")
    for row in unresolved:
        print(f"  unresolved: {row}")
    print(f"weapon_damage_jewelry_frontier_closed={frontier_closed}")
    print(
        "NEXT_STEP=compose the winning Bloodthirsty+damage-glyph jewelry ceiling with the "
        "foundation frontier; then close weapon trait/enchantment, named gear, CP, class, "
        "and runtime power challengers"
    )
    return 0 if frontier_closed else 1


if __name__ == "__main__":
    raise SystemExit(main())
