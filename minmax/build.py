from dataclasses import dataclass, field
from typing import Iterable

from .build_gear import BuildGearSet
from .build_glyph import BuildArmorGlyph
from .build_weapon import BuildWeapon
from .effects import Effect


@dataclass
class Build:
    name: str = "Unnamed Build"

    race_id: int | None = None

    base_stats: dict[str, float] = field(default_factory=dict)
    gear_sets: list[BuildGearSet] = field(default_factory=list)
    armor_glyphs: list[BuildArmorGlyph] = field(default_factory=list)
    weapons: list[BuildWeapon] = field(default_factory=list)
    effects: list[Effect] = field(default_factory=list)

    def add_effect(self, effect: Effect) -> None:
        self.effects.append(effect)

    def add_effects(self, effects: Iterable[Effect]) -> None:
        self.effects.extend(effects)

    def add_gear_set(self, set_id: int, piece_count: int) -> None:
        self.gear_sets.append(
            BuildGearSet(
                set_id=set_id,
                piece_count=piece_count,
            )
        )

    def set_race(self, race_id: int) -> None:
        self.race_id = race_id

    def add_armor_glyph(self, item_id: int) -> None:
        self.armor_glyphs.append(
            BuildArmorGlyph(item_id=item_id)
        )

    def add_weapon(
        self,
        *,
        enchantment_item_id: int | None = None,
        trait: str | None = None,
        quality: str | None = None,
    ) -> None:
        self.weapons.append(
            BuildWeapon(
                enchantment_item_id=enchantment_item_id,
                trait=trait,
                quality=quality,
            )
        )