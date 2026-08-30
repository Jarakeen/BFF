from __future__ import annotations

"""Scribing integration for the Builds page and BuildEditor.

This module is installed at application startup, the same way the shared
searchable build selectors are installed. Keeping the integration isolated
avoids duplicating scribing behavior across the page and editor while the
canonical DB importer is still being extended for crafted skills.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QVBoxLayout,
)

from models.build_model import PlayerBuild
from models.scribing_recipe import ScribedSkillRecipe
from services.scribing_catalog import (
    compatible_affix,
    compatible_focus,
    compatible_signature,
    grimoire_names,
    result_name,
    skill_line_for_grimoire,
)
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard

_INSTALLED = False


def _recipes_for(build: PlayerBuild | None) -> list[ScribedSkillRecipe]:
    if build is None:
        return []
    raw = getattr(build, "ScribedSkillRecipes", None)
    if raw is not None:
        recipes: list[ScribedSkillRecipe] = []
        for value in raw:
            if isinstance(value, ScribedSkillRecipe):
                recipe = value
            elif isinstance(value, dict):
                recipe = ScribedSkillRecipe.from_dict(value)
            else:
                recipe = ScribedSkillRecipe.from_legacy_name(str(value or ""))
            if recipe.ResultName:
                recipes.append(recipe)
        return recipes
    return [
        ScribedSkillRecipe.from_legacy_name(name)
        for name in getattr(build, "ScribedSkills", [])
        if str(name or "").strip()
    ]


def _store_recipes(build: PlayerBuild, recipes: list[ScribedSkillRecipe]) -> None:
    clean = [recipe for recipe in recipes if recipe.ResultName.strip()]
    build.ScribedSkillRecipes = clean
    # Keep the original field as a compatibility mirror. Existing code and
    # older builds know only result names.
    build.ScribedSkills = [recipe.ResultName.strip() for recipe in clean]


class ScribedSkillRecipeDialog(QDialog):
    def __init__(self, recipe: ScribedSkillRecipe | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Build Scribed Skill")
        self.resize(560, 330)
        self._loading = False
        recipe = recipe or ScribedSkillRecipe()

        root = QVBoxLayout(self)
        explanation = QLabel(
            "Choose a Grimoire, then one compatible Focus, Signature, and Affix script. "
            "The result is saved as one configured skill for this build."
        )
        explanation.setWordWrap(True)
        root.addWidget(explanation)

        form = QFormLayout()
        self.grimoire = QComboBox()
        self.grimoire.addItem("")
        self.grimoire.addItems(grimoire_names())
        self.focus = QComboBox()
        self.signature = QComboBox()
        self.affix = QComboBox()
        self.result = QLineEdit()
        self.result.setPlaceholderText("Exact in-game skill name")
        form.addRow("Grimoire", self.grimoire)
        form.addRow("Focus", self.focus)
        form.addRow("Signature", self.signature)
        form.addRow("Affix", self.affix)
        form.addRow("Result Skill", self.result)
        root.addLayout(form)

        self.result_note = QLabel()
        self.result_note.setWordWrap(True)
        root.addWidget(self.result_note)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = FoundryButton("Cancel", role=ButtonRole.SECONDARY, compact=True)
        save = FoundryButton("Save Scribed Skill", role=ButtonRole.PRIMARY, compact=True)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._accept_if_valid)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

        self.grimoire.currentTextChanged.connect(self._refresh_compatible_scripts)
        self.focus.currentTextChanged.connect(self._refresh_result_name)

        self._loading = True
        self.grimoire.setCurrentText(recipe.Grimoire)
        self._refresh_compatible_scripts()
        self.focus.setCurrentText(recipe.Focus)
        self.signature.setCurrentText(recipe.Signature)
        self.affix.setCurrentText(recipe.Affix)
        self.result.setText(recipe.ResultName)
        self._loading = False
        self._refresh_result_name(preserve_existing=bool(recipe.ResultName))

    @staticmethod
    def _replace_combo(combo: QComboBox, values: list[str], current: str = "") -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        combo.addItems(values)
        if current and combo.findText(current, Qt.MatchFlag.MatchExactly) >= 0:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _refresh_compatible_scripts(self, *_args) -> None:
        grimoire = self.grimoire.currentText().strip()
        old_focus = self.focus.currentText().strip()
        old_signature = self.signature.currentText().strip()
        old_affix = self.affix.currentText().strip()
        self._replace_combo(self.focus, compatible_focus(grimoire), old_focus)
        self._replace_combo(self.signature, compatible_signature(grimoire), old_signature)
        self._replace_combo(self.affix, compatible_affix(grimoire), old_affix)
        if not self._loading:
            self._refresh_result_name()

    def _refresh_result_name(self, *_args, preserve_existing: bool = False) -> None:
        mapped = result_name(self.grimoire.currentText(), self.focus.currentText())
        if mapped:
            self.result.setText(mapped)
            self.result_note.setText("Result name verified for this Grimoire + Focus pair.")
        else:
            if not preserve_existing:
                self.result.clear()
            self.result_note.setText(
                "This Grimoire + Focus result name is not normalized yet. "
                "Enter the exact name shown in ESO; the recipe itself will still be preserved."
            )

    def _accept_if_valid(self) -> None:
        missing = [
            label
            for label, value in (
                ("Grimoire", self.grimoire.currentText()),
                ("Focus", self.focus.currentText()),
                ("Signature", self.signature.currentText()),
                ("Affix", self.affix.currentText()),
                ("Result Skill", self.result.text()),
            )
            if not str(value or "").strip()
        ]
        if missing:
            QMessageBox.warning(self, "Incomplete Scribed Skill", "Choose or enter: " + ", ".join(missing))
            return
        self.accept()

    @property
    def recipe(self) -> ScribedSkillRecipe:
        return ScribedSkillRecipe(
            ResultName=self.result.text().strip(),
            Grimoire=self.grimoire.currentText().strip(),
            Focus=self.focus.currentText().strip(),
            Signature=self.signature.currentText().strip(),
            Affix=self.affix.currentText().strip(),
        )


class ScribedSkillsDialog(QDialog):
    def __init__(self, recipes: list[ScribedSkillRecipe], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scribed Skills")
        self.resize(700, 520)
        self._recipes = list(recipes)

        root = QVBoxLayout(self)
        help_text = QLabel(
            "Build the scribed skills configured for this character/build. Saved results are added to the normal "
            "Front/Back skill dropdowns in Edit Build."
        )
        help_text.setWordWrap(True)
        root.addWidget(help_text)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda *_: self._edit())
        root.addWidget(self.list, 1)

        row = QHBoxLayout()
        add = FoundryButton("+ Build Scribed Skill", role=ButtonRole.PRIMARY, compact=True)
        edit = FoundryButton("Edit", role=ButtonRole.SECONDARY, compact=True)
        remove = FoundryButton("Remove", role=ButtonRole.DANGER, compact=True)
        row.addWidget(add)
        row.addWidget(edit)
        row.addWidget(remove)
        row.addStretch()
        cancel = FoundryButton("Cancel", role=ButtonRole.SECONDARY, compact=True)
        save = FoundryButton("Save Scribed Skills", role=ButtonRole.SUCCESS, compact=True)
        row.addWidget(cancel)
        row.addWidget(save)
        root.addLayout(row)

        add.clicked.connect(self._add)
        edit.clicked.connect(self._edit)
        remove.clicked.connect(self._remove)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        self._refresh()

    def _refresh(self) -> None:
        current = self.list.currentRow()
        self.list.clear()
        for recipe in self._recipes:
            detail = recipe.recipe_text or "legacy result-name entry"
            self.list.addItem(f"{recipe.ResultName}\n    {detail}")
        if self.list.count():
            self.list.setCurrentRow(min(max(current, 0), self.list.count() - 1))

    def _add(self) -> None:
        dialog = ScribedSkillRecipeDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._recipes.append(dialog.recipe)
            self._refresh()
            self.list.setCurrentRow(self.list.count() - 1)

    def _edit(self) -> None:
        index = self.list.currentRow()
        if index < 0 or index >= len(self._recipes):
            return
        dialog = ScribedSkillRecipeDialog(self._recipes[index], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._recipes[index] = dialog.recipe
            self._refresh()
            self.list.setCurrentRow(index)

    def _remove(self) -> None:
        index = self.list.currentRow()
        if index < 0 or index >= len(self._recipes):
            return
        del self._recipes[index]
        self._refresh()

    @property
    def recipes(self) -> list[ScribedSkillRecipe]:
        return list(self._recipes)


def _synthetic_skill(recipe: ScribedSkillRecipe) -> dict:
    return {
        "name": recipe.ResultName,
        "is_player": 1,
        "is_passive": 0,
        "is_crafted": 1,
        "skill_line": skill_line_for_grimoire(recipe.Grimoire),
        "class_type": "",
        "base_mechanic": 0,
        "texture": "",
        "scribing_recipe": recipe.to_dict(),
    }


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from widgets.build_editor import BuildEditor

    # ---- PlayerBuild persistence -----------------------------------------
    original_to_dict = PlayerBuild.to_dict
    original_from_dict = PlayerBuild.from_dict

    def to_dict_with_recipes(self: PlayerBuild) -> dict:
        data = original_to_dict(self)
        recipes = _recipes_for(self)
        data["ScribedSkillRecipes"] = [recipe.to_dict() for recipe in recipes]
        data["ScribedSkills"] = [recipe.ResultName for recipe in recipes]
        return data

    def from_dict_with_recipes(cls, data: dict | None) -> PlayerBuild:
        raw = dict(data or {})
        build = original_from_dict(raw)
        raw_recipes = raw.get("ScribedSkillRecipes")
        if raw_recipes is None:
            recipes = [
                ScribedSkillRecipe.from_legacy_name(name)
                for name in raw.get("ScribedSkills", [])
                if str(name or "").strip()
            ]
        else:
            recipes = [
                ScribedSkillRecipe.from_dict(value)
                for value in raw_recipes
                if isinstance(value, dict)
            ]
        _store_recipes(build, recipes)
        return build

    PlayerBuild.to_dict = to_dict_with_recipes
    PlayerBuild.from_dict = classmethod(from_dict_with_recipes)

    # ---- BuildEditor carry-through --------------------------------------
    original_load = BuildEditor.load
    original_model = BuildEditor.model

    def load_with_recipes(self, model: PlayerBuild) -> None:
        self._scribed_skill_recipes = _recipes_for(model)
        original_load(self, model)

    def model_with_recipes(self) -> PlayerBuild:
        build = original_model.fget(self)
        _store_recipes(build, list(getattr(self, "_scribed_skill_recipes", [])))
        return build

    BuildEditor.load = load_with_recipes
    BuildEditor.model = property(model_with_recipes)

    # ---- Builds page card / builder -------------------------------------
    original_editor = BuildsPage._editor

    def editor_with_scribed_recipes(self, build: PlayerBuild | None = None):
        editor = original_editor(self, build)
        recipes = _recipes_for(build)
        existing = {
            str(skill.get("name", "")).strip().casefold()
            for skill in editor.skill_choices
            if isinstance(skill, dict)
        }
        for recipe in recipes:
            if not recipe.ResultName or recipe.ResultName.casefold() in existing:
                continue
            editor.skill_choices.append(_synthetic_skill(recipe))
            existing.add(recipe.ResultName.casefold())
        # SkillBarRow keeps the original list it received at construction;
        # update that source before BuildEditor.load applies the class filter.
        for row in (editor.front_bar, editor.back_bar):
            row.all_skill_choices = editor.skill_choices
        return editor

    def scribed_skills_card(self, build: PlayerBuild):
        card = FoundryCard("Scribed Skills")
        recipes = _recipes_for(build)
        if recipes:
            for recipe in recipes:
                title = QLabel(recipe.ResultName)
                title.setStyleSheet("font-weight:700;")
                card.addWidget(title)
                detail = QLabel(recipe.recipe_text or "Legacy scribed-skill entry; recipe not recorded yet.")
                detail.setWordWrap(True)
                card.addWidget(detail)
        else:
            empty = QLabel("No configured scribed skills for this build.")
            empty.setWordWrap(True)
            card.addWidget(empty)
        actions = QHBoxLayout()
        actions.addStretch()
        button = FoundryButton("Build Scribed Skills", role=ButtonRole.SECONDARY, compact=True)
        button.clicked.connect(self._edit_scribed_skills)
        actions.addWidget(button)
        card.addLayout(actions)
        return card

    def edit_scribed_skills(self) -> None:
        if not self.roster.Members or self.selected_index >= len(self.roster.Members):
            return
        build = self.roster.Members[self.selected_index]
        dialog = ScribedSkillsDialog(_recipes_for(build), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        _store_recipes(build, dialog.recipes)
        self._save()
        self._refresh_detail()

    BuildsPage._editor = editor_with_scribed_recipes
    BuildsPage._scribed_skills_card = scribed_skills_card
    BuildsPage._edit_scribed_skills = edit_scribed_skills

    _INSTALLED = True
