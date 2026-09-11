from models.build_model import PlayerBuild
from minmax.gear_stat_inputs import GearCalculationInputs, GearStatInputResolver
from minmax.mundus_repository import MundusRepository
from minmax.static_build_inputs import StaticBuildInputResolver


def test_player_build_round_trips_second_mundus():
    build = PlayerBuild(Mundus="The Mage", SecondMundus="The Tower")

    restored = PlayerBuild.from_dict(build.to_dict())

    assert restored.Mundus == "The Mage"
    assert restored.SecondMundus == "The Tower"
    assert restored.validate() == []


def test_ordinary_build_serialization_does_not_emit_empty_second_mundus():
    payload = PlayerBuild(Mundus="The Mage").to_dict()

    assert "SecondMundus" not in payload
    assert PlayerBuild.from_dict(payload).SecondMundus == ""


def test_second_mundus_is_appended_after_legacy_positional_fields():
    build = PlayerBuild("Name", "Tag", "Build", "Image", "Race", "Class", "Role", "Alliance", "The Mage")

    assert build.Mundus == "The Mage"
    assert build.SecondMundus == ""


def test_duplicate_second_mundus_fails_model_validation():
    build = PlayerBuild(Mundus="The Mage", SecondMundus="The Mage")

    assert "must be distinct" in build.validate()[0]


def test_second_mundus_requires_active_twice_born_star(monkeypatch, tmp_path):
    repository = MundusRepository(tmp_path / "mundus.db")
    resolver = StaticBuildInputResolver(mundus_repository=repository)
    build = PlayerBuild(Mundus="The Mage", SecondMundus="The Tower")
    monkeypatch.setattr(
        GearStatInputResolver,
        "equipped_set_counts",
        staticmethod(lambda _build, active_bar="front": {}),
    )

    result = resolver.apply(GearCalculationInputs(), build)

    assert result.magicka.mundus_flat > 0
    assert result.stamina.mundus_flat == 0
    assert "Secondary Mundus requires active Twice-Born Star 5-piece bonus" in result.unresolved


def test_active_twice_born_star_applies_both_distinct_mundus(monkeypatch, tmp_path):
    repository = MundusRepository(tmp_path / "mundus.db")
    resolver = StaticBuildInputResolver(mundus_repository=repository)
    build = PlayerBuild(Mundus="The Mage", SecondMundus="The Tower")
    monkeypatch.setattr(
        GearStatInputResolver,
        "equipped_set_counts",
        staticmethod(lambda _build, active_bar="front": {"Twice-Born Star": 5}),
    )

    result = resolver.apply(GearCalculationInputs(), build)

    assert result.unresolved == ()
    assert result.magicka.mundus_flat > 0
    assert result.stamina.mundus_flat > 0
