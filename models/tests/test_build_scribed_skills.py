from models.build_model import PlayerBuild


def test_player_build_round_trips_scribed_skill_access():
    build = PlayerBuild(
        Name="Tank",
        BuildName="Trial Tank",
        ScribedSkills=["Warding Burst", "Healing Soul"],
    )

    restored = PlayerBuild.from_dict(build.to_dict())

    assert restored.ScribedSkills == ["Warding Burst", "Healing Soul"]


def test_legacy_build_without_scribed_skills_loads_empty_access_list():
    restored = PlayerBuild.from_dict({"Name": "Legacy Tank", "BuildName": "Old Build"})

    assert restored.ScribedSkills == []
