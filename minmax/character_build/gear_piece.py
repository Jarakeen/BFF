from dataclasses import dataclass, field
from enum import Enum

from .effect_instance import EffectVariant


class GearSlot(str, Enum):
    """The ten non-weapon equipment slots in ESO."""

    HEAD = "head"
    SHOULDERS = "shoulders"
    CHEST = "chest"
    HANDS = "hands"
    WAIST = "waist"
    LEGS = "legs"
    FEET = "feet"
    NECKLACE = "necklace"
    RING_1 = "ring_1"
    RING_2 = "ring_2"


class GearPieceCategory(str, Enum):
    """What kind of item occupies a gear slot, for hard-constraint checks."""

    SET_PIECE = "set_piece"
    MONSTER_SET = "monster_set"
    MYTHIC = "mythic"
    NORMAL = "normal"


@dataclass(frozen=True)
class ArmorPiece:
    """One piece of armor or jewelry in one of the ten non-weapon slots."""

    slot: GearSlot
    category: GearPieceCategory = GearPieceCategory.NORMAL

    set_id: str | None = None
    """Stable identity of the gear set this piece belongs to, if any."""

    glyph_id: str | None = None
    enchantment_id: str | None = None
    trait: str | None = None
    quality: str | None = None
    level: int | None = None
    weight: str | None = None

    effects: tuple[EffectVariant, ...] = field(default_factory=tuple)
    """Proc/stat effects this specific piece can contribute."""
