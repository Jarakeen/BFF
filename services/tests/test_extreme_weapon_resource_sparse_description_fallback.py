from types import SimpleNamespace

from services.extreme_weapon_resource_relevance_service import (
    ExtremeWeaponResourceRelevanceService,
)


class _EnchantRepository:
    def __init__(self, description):
        self.description = description

    def list_items(self):
        return ((1, "Glyph of Decrease Health"),)

    def get_effects(self, item_id, *, use_max_value=True):
        assert item_id == 1
        assert use_max_value is True
        return ()

    def get_description(self, item_id):
        assert item_id == 1
        return self.description


class _RuleRepository:
    def list_weapon_trait_names(self):
        return ("Charged",)

    def get_weapon_trait_rules(self, name):
        assert name == "Charged"
        return (SimpleNamespace(rule_type="status_effect_chance"),)


def _service(description):
    return ExtremeWeaponResourceRelevanceService(
        enchantment_repository=_EnchantRepository(description),
        rule_repository=_RuleRepository(),
    )


def test_enemy_max_health_scaled_oblivion_damage_is_irrelevant_to_player_max_health():
    audit = _service(
        "Deals 4875 Oblivion Damage based on a portion of the enemy's Max Health."
    ).build("max_health")

    assert audit.denominator_proven is True
    assert audit.objective_irrelevance_proven is True
    assert audit.relevant_enchantments == ()
    assert audit.unresolved == ()


def test_sparse_direct_player_max_health_mutation_remains_relevant():
    audit = _service("Increases your Maximum Health by 1000.").build("max_health")

    assert audit.denominator_proven is True
    assert audit.objective_irrelevance_proven is False
    assert audit.relevant_enchantments == ("Glyph of Decrease Health",)
    assert audit.unresolved == ()
