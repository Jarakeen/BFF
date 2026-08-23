import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from importers.combat_effect_importer import CombatEffectImporter

from minmax.combat_effect_repository import CombatEffectRepository
from minmax.combat_effect_support_resolver import CombatEffectSupportResolver
from minmax.effects import EffectUnit
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType


@pytest.fixture()
def database_path(tmp_path) -> Path:
    """
    Build a throwaway sqlite database populated by the project's real,
    committed CombatEffectImporter - the actual curated ESO status-effect
    catalog (Chilled, Off Balance, etc.), not a fake fixture. This avoids
    touching the shared data/eso.db, which is empty in this environment.

    CombatEffectImporter requires its source file to exist on disk, but
    _build_effects() never reads its contents (the effect data is
    hardcoded in the importer) - so an empty placeholder file satisfies
    that check without fabricating any ESO data ourselves.
    """

    db_path = tmp_path / "combat_effects_test.db"
    source_file = tmp_path / "combat_effects.md"
    source_file.write_text("unused placeholder\n")

    CombatEffectImporter(
        database_path=db_path,
        source_file=source_file,
    ).run()

    return db_path


@pytest.fixture()
def registry(database_path):
    repository = CombatEffectRepository(database_path)
    resolver = CombatEffectSupportResolver(repository)
    return resolver.resolve()


def _by_name(registry, name):
    return [effect for effect in registry.all() if effect.name == name]


def test_repository_loads_real_curated_catalog(database_path):
    repository = CombatEffectRepository(database_path)

    records = repository.get_all()

    assert len(records) > 0
    assert any(record.name == "Chilled" for record in records)


def test_chilled_is_resolved_as_a_status_targeting_enemy(registry):
    matches = _by_name(registry, "Chilled")

    assert len(matches) == 1
    chilled = matches[0]

    assert chilled.category == SupportEffectCategory.STATUS
    assert chilled.target_type == SupportTargetType.ENEMY
    assert chilled.applies_status == "Chilled"
    assert chilled.source == "Frost Damage"


def test_chilled_trigger_is_frost_damage_not_fabricated(registry):
    chilled = _by_name(registry, "Chilled")[0]

    assert chilled.trigger is not None
    assert chilled.trigger.trigger == "on_frost_damage"


def test_frost_chilled_brittle_chain_is_preserved_structurally(registry):
    """
    Frost damage -> Chilled -> Minor Brittle, reconstructed only from the
    database's own trigger/interaction rows.
    """

    chilled = _by_name(registry, "Chilled")[0]
    brittle_matches = _by_name(registry, "Minor Brittle")

    assert len(brittle_matches) == 1
    brittle = brittle_matches[0]

    # Frost damage is the trigger for Chilled, not for Brittle directly.
    assert chilled.trigger.trigger == "on_frost_damage"

    # Brittle requires Chilled to already be present.
    assert brittle.requires_status == "Chilled"
    assert brittle.source == "Chilled"

    # The real database condition (Ice Staff) is preserved, not invented.
    assert brittle.conditions == ("Ice Staff active weapon",)
    assert brittle.target_type == SupportTargetType.ENEMY
    assert brittle.category == SupportEffectCategory.DEBUFF


def test_frost_damage_alone_does_not_become_chilled_or_brittle(registry):
    """
    There is no bare "Frost Damage" SupportEffect in the registry - only
    Chilled (which frost damage triggers) and its interactions exist.
    Frost damage itself is never fabricated as a standalone entry.
    """

    assert _by_name(registry, "Frost Damage") == []
    assert _by_name(registry, "Frost") == []


def test_resistance_reduction_is_recognized_from_schema_unit(registry):
    """
    Sundered -> Minor Breach carries target_unit == "resistance" in the
    real data, which is the only structural signal this resolver uses to
    populate resistance_reduction.
    """

    breach = _by_name(registry, "Minor Breach")[0]

    assert breach.resistance_reduction == 2974
    assert breach.unit == EffectUnit.FLAT
    assert breach.target_type == SupportTargetType.ENEMY
    assert breach.category == SupportEffectCategory.DEBUFF


def test_caster_scoped_interaction_becomes_a_self_buff(registry):
    """
    Sundered also grants "Weapon and Spell Damage" to the Caster - a
    buff on the person who triggered it, not the enemy.
    """

    caster_buff = _by_name(registry, "Weapon and Spell Damage")[0]

    assert caster_buff.category == SupportEffectCategory.BUFF
    assert caster_buff.target_type == SupportTargetType.SELF
    assert caster_buff.magnitude == 100


def test_attacker_scoped_interaction_becomes_a_self_buff(registry):
    """Off Balance empowers the Attacker's Heavy Attack."""

    heavy_attack = _by_name(registry, "Heavy Attack")[0]

    assert heavy_attack.category == SupportEffectCategory.BUFF
    assert heavy_attack.target_type == SupportTargetType.SELF


def test_unsupported_scope_is_skipped_not_guessed(registry):
    """
    Overcharged -> Minor Magickasteal has target_scope "Players damaging
    target", which does not map unambiguously onto self/ally/group/
    enemy. It must not appear in the registry at all.
    """

    assert _by_name(registry, "Minor Magickasteal") == []


def test_hemorrhaging_stacking_is_derived_from_stack_max(registry):
    hemorrhaging = _by_name(registry, "Hemorrhaging")[0]

    assert hemorrhaging.stacking == StackingBehavior.STACKS


def test_chilled_stacking_defaults_to_unique_when_no_stack_max(registry):
    chilled = _by_name(registry, "Chilled")[0]

    assert chilled.stacking == StackingBehavior.UNIQUE


def test_combat_category_effects_are_resolved_as_other(registry):
    """
    "Off Balance" is stored with category "Combat" in the database, not
    "Status" - this must not be relabeled as a status effect.
    """

    off_balance = _by_name(registry, "Off Balance")[0]

    assert off_balance.category == SupportEffectCategory.OTHER
    assert off_balance.applies_status is None


def test_role_relevance_is_not_fabricated(registry):
    """Nothing in this data source ties an effect to a role."""

    for effect in registry.all():
        assert effect.role_relevance == frozenset()


def test_returned_object_is_a_support_effect_registry(registry):
    from minmax.support_effect_registry import SupportEffectRegistry

    assert isinstance(registry, SupportEffectRegistry)
    assert len(registry) > 0
