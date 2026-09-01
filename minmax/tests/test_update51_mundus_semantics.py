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
