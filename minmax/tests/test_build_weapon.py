from minmax.build import Build
from minmax.build_weapon import BuildWeapon


FROST_ENCHANTMENT_ID = 5365


def test_build_starts_with_no_weapons():
    build = Build()

    assert build.weapons == []


def test_build_can_add_weapon():
    build = Build()

    build.add_weapon(
        enchantment_item_id=FROST_ENCHANTMENT_ID,
        trait="Infused",
        quality="Legendary",
    )

    assert build.weapons == [
        BuildWeapon(
            enchantment_item_id=FROST_ENCHANTMENT_ID,
            trait="Infused",
            quality="Legendary",
        )
    ]


def test_build_can_add_weapon_without_enchantment():
    build = Build()

    build.add_weapon(
        trait="Infused",
        quality="Legendary",
    )

    assert build.weapons == [
        BuildWeapon(
            trait="Infused",
            quality="Legendary",
        )
    ]


def test_build_can_contain_multiple_weapons():
    build = Build()

    build.add_weapon(
        enchantment_item_id=FROST_ENCHANTMENT_ID,
        trait="Infused",
        quality="Legendary",
    )

    build.add_weapon(
        enchantment_item_id=None,
        trait="Jade",
        quality="Legendary",
    )

    assert build.weapons == [
        BuildWeapon(
            enchantment_item_id=FROST_ENCHANTMENT_ID,
            trait="Infused",
            quality="Legendary",
        ),
        BuildWeapon(
            enchantment_item_id=None,
            trait="Jade",
            quality="Legendary",
        ),
    ]


def test_build_weapon_is_immutable():
    weapon = BuildWeapon(
        enchantment_item_id=FROST_ENCHANTMENT_ID,
        trait="Infused",
        quality="Legendary",
    )

    try:
        weapon.trait = "Jade"
    except Exception:
        pass
    else:
        raise AssertionError("BuildWeapon should be immutable")
    