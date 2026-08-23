from dataclasses import dataclass, field

from .effect_instance import EffectVariant
from .weapon_type import WeaponType


@dataclass(frozen=True)
class Weapon:
    """
    One weapon equipped in one hand slot on one bar.

    Weapons (unlike armor/jewelry) are inherently bar-specific in ESO:
    the front bar and back bar each carry their own main/off hand
    weapons, traits, and enchantments, and only the skill line(s) tied
    to the bar's own weapon configuration are available on that bar.
    """

    weapon_type: WeaponType
    trait: str | None = None
    enchantment_id: str | None = None
    set_id: str | None = None
    """Stable identity of a gear set this weapon belongs to, if any."""

    enchantment_item_id: int | None = None
    """
    The ESO database item id for this weapon's enchantment, if known. This
    is separate from `enchantment_id` (a stable snake_case identity, may
    be unset) - it exists purely to bridge into the existing DB-backed
    WeaponEnchantmentRepository/WeaponEnchantmentEffectService pipeline.
    """

    quality: str | None = None
    """Item quality (e.g. "Legendary"), used by trait-rule resolution."""

    effects: tuple[EffectVariant, ...] = field(default_factory=tuple)
    """Proc/stat effects this specific weapon can contribute."""
