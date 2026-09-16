from services.build_enchant_catalog_service import BuildEnchantCatalogService


class _ArmorRepository:
    def list_names(self):
        return (
            "Lesser Glyph of Magicka",
            "Truly Superb Glyph of Magicka",
            "Glyph of Prismatic Defense",
        )


class _JewelryRepository:
    def list_names(self):
        return (
            "Lesser Glyph of Bashing",
            "Truly Superb Glyph of Bashing",
            "Glyph of Bracing",
            "Glyph of Increase Magical Harm",
        )


class _WeaponRepository:
    def list_items(self):
        return (
            (1, "Lesser Glyph of Crushing"),
            (2, "Truly Superb Glyph of Crushing"),
            (3, "Glyph of Flame"),
        )


def _service(tmp_path):
    return BuildEnchantCatalogService(
        tmp_path / "unused.db",
        armor_repository=_ArmorRepository(),
        jewelry_repository=_JewelryRepository(),
        weapon_repository=_WeaponRepository(),
    )


def test_catalog_keeps_equipment_families_separate(tmp_path):
    service = _service(tmp_path)

    assert service.armor_choices() == ("", "Max Magicka", "Prismatic Defense")
    assert service.jewelry_choices() == (
        "",
        "Bashing",
        "Block Cost",
        "Spell Damage",
    )
    assert service.weapon_choices() == ("", "Glyph of Crushing", "Glyph of Flame")


def test_catalog_collapses_item_tiers_without_losing_family_identity(tmp_path):
    service = _service(tmp_path)

    assert service.armor_choices().count("Max Magicka") == 1
    assert service.jewelry_choices().count("Bashing") == 1
    assert service.weapon_choices().count("Glyph of Crushing") == 1
