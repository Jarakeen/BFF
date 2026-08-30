from models.build_model import PlayerBuild


def test_attribute_points_round_trip():
    build = PlayerBuild(
        AttributeHealth=20,
        AttributeMagicka=44,
        AttributeStamina=0,
        Vampire=True,
    )

    restored = PlayerBuild.from_dict(build.to_dict())

    assert restored.AttributeHealth == 20
    assert restored.AttributeMagicka == 44
    assert restored.AttributeStamina == 0
    assert restored.attribute_points_total == 64
    assert restored.Vampire is True
    assert restored.Werewolf is False


def test_attribute_points_may_be_incomplete_while_editing():
    build = PlayerBuild(AttributeHealth=10, AttributeMagicka=20, AttributeStamina=5)

    assert build.attribute_points_total == 35
    assert build.validate() == []


def test_attribute_points_cannot_exceed_lifetime_pool():
    build = PlayerBuild(AttributeHealth=30, AttributeMagicka=30, AttributeStamina=10)

    assert build.attribute_points_total == 70
    assert "Attribute points cannot exceed 64." in build.validate()
