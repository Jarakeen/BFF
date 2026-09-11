from types import SimpleNamespace

from services.extreme_weapon_resource_relevance_service import (
    ExtremeWeaponResourceRelevanceService,
)


class _EnchantRepository:
    def __init__(self, effects_by_id):
        self.effects_by_id = effects_by_id

    def list_items(self):
        return tuple((item_id, f"Enchant {item_id}") for item_id in sorted(self.effects_by_id))

    def get_effects(self, item_id, *, use_max_value=True):
        assert use_max_value is True
        return tuple(
            SimpleNamespace(effect_type=effect_type)
            for effect_type in self.effects_by_id[item_id]
        )


class _RuleRepository:
    def __init__(self, rules_by_name):
        self.rules_by_name = rules_by_name

    def list_weapon_trait_names(self):
        return tuple(sorted(self.rules_by_name))

    def get_weapon_trait_rules(self, name):
        return tuple(
            SimpleNamespace(rule_type=rule_type)
            for rule_type in self.rules_by_name[name]
        )


def _service(*, effects=None, rules=None):
    return ExtremeWeaponResourceRelevanceService(
        enchantment_repository=_EnchantRepository(
            effects
            or {
                1: ("damage",),
                2: ("health_restore",),
                3: ("weapon_spell_damage",),
            }
        ),
        rule_repository=_RuleRepository(
            rules
            or {
                "Charged": ("status_effect_chance",),
                "Infused": (
                    "weapon_enchantment_effect",
                    "enchantment_cooldown_reduction",
                ),
                "Nirnhoned": ("weapon_damage",),
                "Precise": ("weapon_spell_critical",),
            }
        ),
    )


def test_current_resource_restore_is_irrelevant_to_max_resource():
    audit = _service().build("max_health")

    assert audit.objective_irrelevance_proven is True
    assert audit.relevant_enchantments == ()
    assert audit.relevant_traits == ()
    assert audit.enchantments_reviewed == 3
    assert audit.traits_reviewed == 4
    assert "health_restore" in audit.enchant_effect_types_reviewed


def test_direct_max_resource_weapon_enchant_blocks_irrelevance():
    audit = _service(effects={1: ("max_health",)}).build("max_health")

    assert audit.denominator_proven is True
    assert audit.objective_irrelevance_proven is False
    assert audit.relevant_enchantments == ("Enchant 1",)


def test_direct_target_resource_trait_blocks_irrelevance():
    audit = _service(rules={"Impossible Trait": ("max_magicka",)}).build("max_magicka")

    assert audit.denominator_proven is True
    assert audit.objective_irrelevance_proven is False
    assert audit.relevant_traits == ("Impossible Trait",)


def test_unknown_enchantment_effect_fails_closed():
    audit = _service(effects={1: ("mystery_resource_magic",)}).build("max_stamina")

    assert audit.denominator_proven is False
    assert audit.objective_irrelevance_proven is False
    assert any("Unreviewed weapon enchantment effect type" in row for row in audit.unresolved)


def test_unknown_trait_rule_fails_closed():
    audit = _service(rules={"Mystery": ("mystery_trait_rule",)}).build("max_health")

    assert audit.denominator_proven is False
    assert audit.objective_irrelevance_proven is False
    assert any("Unreviewed weapon trait rule type" in row for row in audit.unresolved)


def test_empty_or_unmapped_catalog_rows_fail_closed():
    empty = ExtremeWeaponResourceRelevanceService(
        enchantment_repository=_EnchantRepository({}),
        rule_repository=_RuleRepository({}),
    ).build("max_health")
    assert empty.denominator_proven is False

    missing = _service(effects={1: ()}, rules={"Trait": ()}).build("max_health")
    assert missing.denominator_proven is False
    assert any("no mapped effects" in row for row in missing.unresolved)
    assert any("no mapped rules" in row for row in missing.unresolved)


def test_unsupported_objective_fails_closed():
    service = _service()
    try:
        service.build("spell_damage")
    except KeyError as exc:
        assert "unreviewed Extreme weapon resource objective" in str(exc)
    else:
        raise AssertionError("expected unsupported objective to fail closed")
