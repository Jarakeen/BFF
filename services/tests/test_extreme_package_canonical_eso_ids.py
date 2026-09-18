from __future__ import annotations

from minmax.character_build.weapon_type import WeaponType
from minmax.eso_weapon_type_id import eso_weapon_type_id
from services.extreme_actual_heal_arena_weapon_package_service import (
    ExtremeActualHealArenaWeaponPackageService,
)
from services.extreme_actual_heal_mythic_package_service import (
    ExtremeActualHealMythicPackageService,
)
from services.extreme_actual_heal_non_ring_mythic_package_service import (
    ExtremeActualHealNonRingMythicPackageService,
)
from services.stickerbook_service import EQUIP_TYPES, WEAPON_TYPES


def test_extreme_package_ids_match_canonical_eso_import_identity() -> None:
    assert EQUIP_TYPES[2] == "Necklace"
    assert EQUIP_TYPES[6] == "Two Hand"
    assert EQUIP_TYPES[12] == "Ring"
    assert EQUIP_TYPES[13] == "Hands"

    assert ExtremeActualHealMythicPackageService.NECK_EQUIP_TYPE == 2
    assert ExtremeActualHealMythicPackageService.RING_EQUIP_TYPE == 12
    assert ExtremeActualHealMythicPackageService.TWO_HAND_EQUIP_TYPE == 6
    assert ExtremeActualHealNonRingMythicPackageService.TWO_HAND_EQUIP_TYPE == 6
    assert ExtremeActualHealArenaWeaponPackageService.TWO_HAND_EQUIP_TYPE == 6

    assert WEAPON_TYPES[14] == "Shield"
    assert eso_weapon_type_id(WeaponType.SHIELD) == 14
