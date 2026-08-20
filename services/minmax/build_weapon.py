from dataclasses import dataclass


@dataclass(frozen=True)
class BuildWeapon:
    """A weapon currently equipped by a build."""

    enchantment_item_id: int | None = None
    trait: str | None = None
    quality: str | None = None