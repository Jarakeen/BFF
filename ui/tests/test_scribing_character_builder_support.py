from types import SimpleNamespace

from models.scribing_recipe import ScribedSkillRecipe
from ui import scribing_simulator_support as support
from ui.components import foundry_sidebar


class _FakeClassCombo:
    def currentText(self):
        return "Necromancer"


class _FakeSkillRow:
    def __init__(self):
        self.all_skill_choices = []
        self.classes = []

    def set_class(self, value):
        self.classes.append(value)


class _FakeEditor:
    def __init__(self):
        self.skill_choices = [
            {
                "name": "Venom Skull",
                "is_player": 1,
                "is_passive": 0,
                "skill_line": "Grave Lord",
            },
            {
                "name": "Old Scribed Skill",
                "is_player": 1,
                "is_passive": 0,
                "skill_line": "Support",
                "scribing_recipe": {"ResultName": "Old Scribed Skill"},
            },
        ]
        self._scribed_skill_recipes = [
            ScribedSkillRecipe(
                ResultName="Magical Banner",
                Grimoire="Banner Bearer",
                Focus="Magic Damage",
                Signature="Class Mastery",
                Affix="Heroism",
            )
        ]
        self.eso_class = _FakeClassCombo()
        self.front_bar = _FakeSkillRow()
        self.back_bar = _FakeSkillRow()
        self._boss_cards = []


def test_live_editor_recomposes_scribed_skill_choices() -> None:
    editor = _FakeEditor()

    support._refresh_editor_skill_choices(editor)

    names = [skill["name"] for skill in editor.skill_choices]
    assert names == ["Venom Skull", "Magical Banner"]
    magical = editor.skill_choices[1]
    assert magical["skill_line"] == "Support"
    assert magical["scribing_recipe"]["Grimoire"] == "Banner Bearer"
    assert editor.front_bar.all_skill_choices is editor.skill_choices
    assert editor.back_bar.all_skill_choices is editor.skill_choices
    assert editor.front_bar.classes == ["Necromancer"]
    assert editor.back_bar.classes == ["Necromancer"]


def test_standalone_scribing_route_is_removed(monkeypatch) -> None:
    sections = [
        {
            "label": "Tool",
            "children": [
                ("Other Tool", "other_tool"),
                ("Scribing Simulator", "scribing_simulator"),
            ],
        },
        {"label": "Build", "children": [("Builds", "builds")]},
    ]
    monkeypatch.setattr(foundry_sidebar, "CORE_NAV_SECTIONS", sections)

    support._remove_standalone_navigation()

    assert sections[0]["children"] == [("Other Tool", "other_tool")]
    assert sections[1]["children"] == [("Builds", "builds")]
