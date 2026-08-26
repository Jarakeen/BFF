from models.build_model import PlayerBuild


def test_vampire_state_round_trips():
    build = PlayerBuild(Vampire=True)
    restored = PlayerBuild.from_dict(build.to_dict())
    assert restored.Vampire is True
    assert restored.Werewolf is False
    assert restored.validate() == []


def test_werewolf_state_round_trips():
    build = PlayerBuild(Werewolf=True)
    restored = PlayerBuild.from_dict(build.to_dict())
    assert restored.Werewolf is True
    assert restored.Vampire is False
    assert restored.validate() == []


def test_vampire_and_werewolf_are_invalid_together():
    build = PlayerBuild(Vampire=True, Werewolf=True)
    assert build.validate() == ["A character cannot be both Vampire and Werewolf."]
