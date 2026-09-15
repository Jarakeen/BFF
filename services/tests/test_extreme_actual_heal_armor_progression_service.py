from __future__ import annotations

from minmax.character_progression import CharacterProgression
from services.extreme_actual_heal_armor_progression_service import (
    ExtremeActualHealArmorProgressionService,
)


class _ClassProgression:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def normalize(self, progression, route):
        self.calls.append((progression, route))
        return self.result


class _SkillLines:
    ranks = {
        "Agility": 2,
        "Dexterity": 3,
        "Undaunted Mettle": 2,
    }

    def passive_max_rank(self, name):
        return self.ranks.get(name)


def test_h1_armor_progression_adds_only_reviewed_nonclass_lines_and_max_ranks():
    baseline = CharacterProgression(
        owned_skill_lines=("Restoring Light",),
        passive_ranks={"Existing Passive": 2, "Agility": 1},
    )
    normalized_class = CharacterProgression(
        owned_skill_lines=("Restoring Light", "Aedric Spear"),
        passive_ranks={"Existing Passive": 2, "Agility": 1},
    )
    class_progression = _ClassProgression(normalized_class)
    service = ExtremeActualHealArmorProgressionService(
        class_progression_service=class_progression,
        skill_line_repository=_SkillLines(),
    )
    route = object()

    result = service.normalize(baseline, route)

    assert class_progression.calls == [(baseline, route)]
    assert result.owns_skill_line("Medium Armor") is True
    assert result.owns_skill_line("Undaunted") is True
    assert result.passive_rank("Agility") == 2
    assert result.passive_rank("Dexterity") == 3
    assert result.passive_rank("Undaunted Mettle") == 2
    assert result.passive_rank("Existing Passive") == 2
    assert result.owned_skill_lines[:2] == ("Restoring Light", "Aedric Spear")


def test_h1_armor_progression_replaces_differently_cased_passive_identity():
    normalized_class = CharacterProgression(
        owned_skill_lines=("Medium Armor",),
        passive_ranks={"agility": 1, "DEXTERITY": 1, "undaunted mettle": 1},
    )
    service = ExtremeActualHealArmorProgressionService(
        class_progression_service=_ClassProgression(normalized_class),
        skill_line_repository=_SkillLines(),
    )

    result = service.normalize(CharacterProgression(), object())

    keys = {name.casefold(): name for name in result.passive_ranks}
    assert keys["agility"] == "Agility"
    assert keys["dexterity"] == "Dexterity"
    assert keys["undaunted mettle"] == "Undaunted Mettle"
    assert len([name for name in result.passive_ranks if name.casefold() == "agility"]) == 1


def test_h1_armor_progression_fails_closed_when_canonical_max_rank_is_missing():
    class _MissingSkillLines:
        def passive_max_rank(self, name):
            return None if name == "Dexterity" else 2

    service = ExtremeActualHealArmorProgressionService(
        class_progression_service=_ClassProgression(CharacterProgression()),
        skill_line_repository=_MissingSkillLines(),
    )

    try:
        service.normalize(CharacterProgression(), object())
    except ValueError as exc:
        assert "Dexterity" in str(exc)
    else:
        raise AssertionError("missing canonical armor passive rank must fail closed")
