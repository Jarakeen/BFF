from minmax.coverage_classification import CoverageClassification
from minmax.custom_roster_lab import CustomRosterLab
from minmax.role import Role


def test_custom_roster_can_be_built_and_evaluated():
    lab = CustomRosterLab()
    lab.add_player("Tank", Role.TANK, ["major_breach", "major_protection"])
    lab.add_player("Healer", Role.HEALER, ["major_courage", "major_sorcery", "minor_brittle"])
    lab.add_player("DD", Role.DD, ["major_force"])

    evaluation = lab.evaluate()

    assert len(lab.players) == 3
    assert evaluation.is_fully_covered


def test_custom_roster_can_expose_missing_support():
    lab = CustomRosterLab()
    lab.add_player("DD", Role.DD, ["major_force"])

    evaluation = lab.evaluate()

    assert any(
        result.classification == CoverageClassification.MISSING
        for result in evaluation.classifications
    )


def test_custom_roster_uptime_is_preserved():
    lab = CustomRosterLab()
    lab.add_player("Healer", Role.HEALER, ["major_courage"], uptime=0.79)

    evaluation = lab.evaluate()
    result = evaluation.classification_for_effect("major_courage")

    assert result is not None
    assert result.classification == CoverageClassification.INSUFFICIENT


def test_custom_roster_is_disposable():
    lab = CustomRosterLab()
    lab.add_player("A", Role.DD)
    lab.add_player("B", Role.HEALER)
    lab.remove_player(0)
    assert [player.name for player in lab.players] == ["B"]
    lab.clear()
    assert lab.players == []
