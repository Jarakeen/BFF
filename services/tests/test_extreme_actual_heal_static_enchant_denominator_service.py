from __future__ import annotations

from services.extreme_actual_heal_static_enchant_denominator_service import (
    ExtremeActualHealStaticEnchantDenominatorService,
)


class _ArmorRepo:
    def list_names(self):
        return (
            "Truly Superb Glyph of Health",
            "Truly Superb Glyph of Magicka",
            "Truly Superb Glyph of Stamina",
            "Truly Superb Glyph of Prismatic Defense",
        )


class _JewelryRepo:
    def list_names(self):
        return (
            "Truly Superb Glyph of Increase Physical Harm",
            "Truly Superb Glyph of Increase Magical Harm",
            "Truly Superb Glyph of Magicka Recovery",
            "Truly Superb Glyph of Stamina Recovery",
            "Truly Superb Glyph of Health Recovery",
            "Truly Superb Glyph of Bashing",
            "Truly Superb Glyph of Bracing",
        )

    def get_jewelry_glyph_effect_types_by_name(self, name):
        key = str(name).casefold()
        if "physical harm" in key or name == "Weapon Damage":
            return ("weapon_damage",)
        if "magical harm" in key or name == "Spell Damage":
            return ("spell_damage",)
        if "magicka recovery" in key or name == "Magicka Recovery":
            return ("magicka_recovery",)
        if "stamina recovery" in key or name == "Stamina Recovery":
            return ("stamina_recovery",)
        if "health recovery" in key or name == "Health Recovery":
            return ("health_recovery",)
        if "bashing" in key:
            return ("bash_damage",)
        if "bracing" in key:
            return ("block_cost_reduction",)
        return ()


class _FutureJewelryRepo(_JewelryRepo):
    def list_names(self):
        return (*super().list_names(), "Glyph of Future Healing")

    def get_jewelry_glyph_effect_types_by_name(self, name):
        if name == "Glyph of Future Healing":
            return ("healing_done",)
        return super().get_jewelry_glyph_effect_types_by_name(name)


def test_static_enchant_denominator_accounts_for_reviewed_fixture() -> None:
    result = ExtremeActualHealStaticEnchantDenominatorService(
        "unused.db",
        armor_repository=_ArmorRepo(),
        jewelry_repository=_JewelryRepo(),
    ).build()

    assert result.denominator_proven is True
    assert result.unresolved == ()
    assert set(result.searched_armor_families) == {
        "max health",
        "max magicka",
        "max stamina",
        "prismatic defense",
    }
    assert set(result.searched_jewelry_families) == {
        "weapon damage",
        "spell damage",
        "magicka recovery",
        "stamina recovery",
        "health recovery",
    }
    assert set(result.irrelevant_jewelry_families) == {
        "glyph of bashing",
        "glyph of bracing",
    }


def test_static_enchant_denominator_fails_closed_for_unsearched_relevant_family() -> None:
    result = ExtremeActualHealStaticEnchantDenominatorService(
        "unused.db",
        armor_repository=_ArmorRepo(),
        jewelry_repository=_FutureJewelryRepo(),
    ).build()

    assert result.denominator_proven is False
    assert any("future healing" in message.casefold() for message in result.unresolved)
    assert any("healing_done" in message for message in result.unresolved)
