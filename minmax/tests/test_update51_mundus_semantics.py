from __future__ import annotations

from minmax.mundus_repository import MundusRepository
from minmax.effects import EffectOperation, EffectUnit
from minmax.stat_ids import StatId


def _values(effects):
    return {effect.stat: effect.value for effect in effects}


def test_u50_warrior_remains_weapon_damage_only(tmp_path):
    repository = MundusRepository(tmp_path / "eso.db", game_update=50)

    effects, unresolved = repository.get_effects("The Warrior")

    assert unresolved == []
    assert _values(effects) == {StatId.WEAPON_DAMAGE: 238.0}


def test_thief_rating_is_a_flat_effect_for_critical_chance_conversion(tmp_path):
    repository = MundusRepository(tmp_path / "eso.db", game_update=50)
    effects, unresolved = repository.get_effects("The Thief")

    assert unresolved == []
    assert len(effects) == 1
    assert effects[0].stat is StatId.CRITICAL_CHANCE
    assert effects[0].operation is EffectOperation.ADD
    assert effects[0].unit is EffectUnit.FLAT
    assert effects[0].value == 1333.0


def test_u51_pts_warrior_grants_both_weapon_and_spell_damage(tmp_path):
    repository = MundusRepository(tmp_path / "eso.db", game_update=51)

    effects, unresolved = repository.get_effects("The Warrior")

    assert unresolved == []
    assert _values(effects) == {
        StatId.WEAPON_DAMAGE: 238.0,
        StatId.SPELL_DAMAGE: 238.0,
    }


def test_u50_apprentice_remains_spell_damage(tmp_path):
    repository = MundusRepository(tmp_path / "eso.db", game_update=50)

    effects, unresolved = repository.get_effects("The Apprentice")

    assert unresolved == []
    assert _values(effects) == {StatId.SPELL_DAMAGE: 238.0}


def test_u51_pts_apprentice_is_reference_only_and_not_combat_spell_damage(tmp_path):
    repository = MundusRepository(tmp_path / "eso.db", game_update=51)

    effects, unresolved = repository.get_effects("The Apprentice")

    assert effects == []
    assert len(unresolved) == 2
    assert any("Experience gain" in message for message in unresolved)
    assert any("Inspiration gain" in message for message in unresolved)


def test_get_effects_preserves_public_list_api_and_multiplier(tmp_path):
    repository = MundusRepository(tmp_path / "eso.db", game_update=50)

    effects, unresolved = repository.get_effects("The Ritual", multiplier=1.5)
    canonical_effects, canonical_unresolved = repository.effects_for_name(
        "The Ritual",
        divines_multiplier=1.5,
    )

    assert isinstance(effects, list)
    assert isinstance(unresolved, list)
    assert effects == list(canonical_effects)
    assert unresolved == list(canonical_unresolved)
    assert unresolved == []
    assert _values(effects) == {StatId.HEALING_DONE: 12.0}


def test_get_records_preserves_public_list_api(tmp_path):
    repository = MundusRepository(tmp_path / "eso.db", game_update=50)

    records = repository.get_records("The Mage")

    assert isinstance(records, list)
    assert records == list(repository.records_for_name("The Mage"))
    assert len(records) == 1
    assert records[0].stat_id == StatId.MAX_MAGICKA.value
