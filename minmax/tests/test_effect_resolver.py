from minmax.effect_resolver import EffectResolver
from minmax.effects import EffectOperation, EffectUnit
from minmax.stat_ids import StatId


resolver = EffectResolver()


def test_major_brutality():
    effects = resolver.resolve(
        name="Brutality",
        description="Increases weapon damage by 20%.",
    )

    assert len(effects) == 1
    assert effects[0].stat == StatId.WEAPON_DAMAGE
    assert effects[0].operation == EffectOperation.ADD_PERCENT
    assert effects[0].value == 20
    assert effects[0].unit == EffectUnit.PERCENT


def test_major_sorcery():
    effects = resolver.resolve(
        name="Sorcery",
        description="Increases spell damage by 20%.",
    )

    assert len(effects) == 1
    assert effects[0].stat == StatId.SPELL_DAMAGE
    assert effects[0].value == 20


def test_major_courage_creates_two_effects():
    effects = resolver.resolve(
        name="Courage",
        description="Increase your Weapon and Spell Damage by 430",
    )

    assert len(effects) == 2
    assert {effect.stat for effect in effects} == {
        StatId.WEAPON_DAMAGE,
        StatId.SPELL_DAMAGE,
    }
    assert all(effect.value == 430 for effect in effects)


def test_major_resolve_creates_two_effects():
    effects = resolver.resolve(
        name="Resolve",
        description="Increases physical and spell resistance by 5948.",
    )

    assert len(effects) == 2
    assert {effect.stat for effect in effects} == {
        StatId.PHYSICAL_RESISTANCE,
        StatId.SPELL_RESISTANCE,
    }
    assert all(effect.value == 5948 for effect in effects)


def test_prophecy():
    effects = resolver.resolve(
        name="Prophecy",
        description="Increases spell critical by 2629.",
    )

    assert len(effects) == 1
    assert effects[0].stat == StatId.SPELL_CRITICAL
    assert effects[0].value == 2629


def test_force():
    effects = resolver.resolve(
        name="Force",
        description="Increases critical damage done by 20%.",
    )

    assert len(effects) == 1
    assert effects[0].stat == StatId.CRITICAL_DAMAGE
    assert effects[0].value == 20


def test_mending():
    effects = resolver.resolve(
        name="Mending",
        description="Increases healing done by 16%.",
    )

    assert len(effects) == 1
    assert effects[0].stat == StatId.HEALING_DONE
    assert effects[0].value == 16


def test_debuff_is_not_a_self_stat():
    effects = resolver.resolve(
        name="Breach",
        description="Decreases target's physical and spell resistance by 5948.",
        category="debuff",
    )

    assert effects == []


def test_target_effect_is_not_a_self_stat():
    effects = resolver.resolve(
        name="Cowardice",
        description="Reduces the target's Weapon and Spell Damage by 430",
        category="buff",
    )

    assert effects == []


def test_unknown_effect_is_not_guessed():
    effects = resolver.resolve(
        name="Some Future ESO Nonsense",
        description="Does something mysterious and undocumented.",
    )

    assert effects == []
