from __future__ import annotations

from minmax.mundus_repository import MundusRepository
from minmax.stat_ids import StatId


def _values(effects):
    return {effect.stat: effect.value for effect in effects}


def test_u50_warrior_remains_weapon_damage_only(tmp_path):
    repository = MundusRepository(tmp_path / "eso.db", game_update=50)

    effects, unresolved = repository.get_effects("The Warrior")

    assert unresolved == []
    assert _values(effects) == {StatId.WEAPON_DAMAGE: 238.0}


def test_u51_warrior_grants_both_weapon_and_spell_damage(tmp_path):
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


def test_u51_apprentice_no_longer_inflates_combat_spell_damage(tmp_path):
    repository = MundusRepository(tmp_path / "eso.db", game_update=51)

    effects, unresolved = repository.get_effects("The Apprentice")

    assert effects == []
    assert len(unresolved) == 2
    assert any("experience_gain" in message for message in unresolved)
    assert any("inspiration_gain" in message for message in unresolved)


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
