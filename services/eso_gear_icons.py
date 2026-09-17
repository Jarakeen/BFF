from __future__ import annotations

from pathlib import Path


_ASSET_ROOT = Path(__file__).resolve().parent.parent / "assets" / "icons"


GEAR_SLOT_ICONS = {
    "head": "viking-helmet.svg",
    "shoulders": "spiked-shoulder-armor.svg",
    "chest": "leather-armor.svg",
    "hands": "mailed-fist.svg",
    "legs": "greaves.svg",
    "feet": "metal-boot.svg",
    "waist": "metal-skirt.svg",
    "neck": "heart-necklace.svg",
    "ring1": "ring.svg",
    "ring2": "ring.svg",
    # Legacy keys retained for callers/saved UI layouts.
    "main_hand": "lunar-wand.svg",
    "off_hand": "shield.svg",
    # Explicit front/back weapon rows introduced by the Phase 2 weapon model.
    "front_main_hand": "lunar-wand.svg",
    "front_off_hand": "shield.svg",
    "back_main_hand": "lunar-wand.svg",
    "back_off_hand": "shield.svg",
}


def gear_icon_path(slot: str) -> Path | None:
    filename = GEAR_SLOT_ICONS.get(slot)

    if not filename:
        return None

    path = _ASSET_ROOT / filename

    return path if path.exists() else None
