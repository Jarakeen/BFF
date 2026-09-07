from __future__ import annotations

"""Scribing integration for the Builds page and BuildEditor.

The builder prefers the normalized Update 51 PTS scribing catalog in eso.db.
Static compatibility remains as a compatibility fallback for databases that
have not yet imported the U51 catalog.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
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

from engine.config import DEFAULT_DATABASE
from models.build_model import PlayerBuild
from models.scribing_recipe import ScribedSkillRecipe
from services.eso_icon_resolver import EsoIconResolver
from services.scribing_catalog import (
    compatible_affix as static_compatible_affix,
    compatible_focus as static_compatible_focus,
    compatible_signature as static_compatible_signature,
    grimoire_names as static_grimoire_names,
    result_name as static_result_name,
    skill_line_for_grimoire,
)
from services.scribing_icons import texture_for_scribed_skill
from services.scribing_u51_service import U51ScribingService
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
    build.ScribedSkills = [recipe.ResultName.strip() for recipe in clean]


class ScribedSkillRecipeDialog(QDialog):
    def __init__(self, recipe: ScribedSkillRecipe | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Build Scribed Skill")
        self.resize(650, 430)
        self._loading = False
        self._u51 = U51ScribingService(DEFAULT_DATABASE)
        self._icon_resolver = EsoIconResolver()
        recipe = recipe or ScribedSkillRecipe()

        root = QVBoxLayout(self)
        explanation = QLabel(
            "Choose a Grimoire, then one compatible Focus, Signature, and Affix script. "
            "Update 51 catalog data is used when available."
        )
        explanation.setWordWrap(True)
        root.addWidget(explanation)

        form = QFormLayout()
        self.grimoire = QComboBox()
        self.grimoire.addItem("")
        names = self._u51.grimoire_names() if self._u51.available else static_grimoire_names()
        self.grimoire.addItems(names)
        self.focus = QComboBox()
        self.signature = QComboBox()
        self.affix = QComboBox()
        self.result = QLineEdit()
        self.result.setPlaceholderText("Exact in-game skill name")
        form.addRow("Grimoire", self.grimoire)
        form.addRow("Focus", self.focus)
        form.addRow("Signature", self.signature)
        form.addRow("Affix", self.affix)

        result_row = QHBoxLayout()
        self.result_icon = QLabel()
        self.result_icon.setFixedSize(48, 48)
        self.result_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_row.addWidget(self.result_icon)
        result_row.addWidget(self.result, 1)
        form.addRow("Result Skill", result_row)
        root.addLayout(form)

        self.result_note = QLabel()
        self.result_note.setWordWrap(True)
        self.result_note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
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
        self.focus.currentTextChanged.connect(self._refresh_result)
        self.signature.currentTextChanged.connect(self._refresh_result)
        self.affix.currentTextChanged.connect(self._refresh_result)

        self._loading = True
        self.grimoire.setCurrentText(recipe.Grimoire)
        self._refresh_compatible_scripts()
        self.focus.setCurrentText(recipe.Focus)
        self.signature.setCurrentText(recipe.Signature)
        self.affix.setCurrentText(recipe.Affix)
        self.result.setText(recipe.ResultName)
        self._loading = False
        self._refresh_result(preserve_existing=bool(recipe.ResultName))

    @staticmethod
    def _replace_combo(combo: QComboBox, values: list[str], current: str = "") -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        combo.addItems(values)
        if current and combo.findText(current, Qt.MatchFlag.MatchExactly) >= 0:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _choices(self, kind: str, grimoire: str) -> list[str]:
        if self._u51.available:
            if kind == "focus":
                return self._u51.compatible_focus(grimoire)
            if kind == "signature":
                return self._u51.compatible_signature(grimoire)
            return self._u51.compatible_affix(grimoire)
        if kind == "focus":
            return static_compatible_focus(grimoire)
        if kind == "signature":
            return static_compatible_signature(grimoire)
        return static_compatible_affix(grimoire)

    def _refresh_compatible_scripts(self, *_args) -> None:
        grimoire = self.grimoire.currentText().strip()
        old_focus = self.focus.currentText().strip()
        old_signature = self.signature.currentText().strip()
        old_affix = self.affix.currentText().strip()
        self._replace_combo(self.focus, self._choices("focus", grimoire), old_focus)
        self._replace_combo(self.signature, self._choices("signature", grimoire), old_signature)
        self._replace_combo(self.affix, self._choices("affix", grimoire), old_affix)
        if not self._loading:
            self._refresh_result()

    def _refresh_icon(self) -> None:
        texture = texture_for_scribed_skill(
            self.grimoire.currentText(),
            self.focus.currentText(),
        )
        path = self._icon_resolver.resolve(texture)
        self.result_icon.clear()
        self.result_icon.setToolTip(texture or "No mapped scribed-skill texture")
        if path is None:
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return
        self.result_icon.setPixmap(
            pixmap.scaled(
                44,
                44,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _refresh_result(self, *_args, preserve_existing: bool = False) -> None:
        grimoire = self.grimoire.currentText().strip()
        focus = self.focus.currentText().strip()
        signature = self.signature.currentText().strip()
        affix = self.affix.currentText().strip()

        mapped = self._u51.result_name(grimoire, focus) if self._u51.available else ""
        if not mapped:
            mapped = static_result_name(grimoire, focus)

        if mapped:
            self.result.setText(mapped)
            self.result.setReadOnly(True)
        else:
            self.result.setReadOnly(False)
            if not preserve_existing:
                self.result.clear()

        self._refresh_icon()

        if self._u51.available:
            detail = self._u51.combined_description(grimoire, focus, signature, affix)
            if mapped:
                prefix = "Update 51 result resolved from the canonical scribing catalog."
            else:
                prefix = "Update 51 compatibility resolved; result name is not available for this selection."
            self.result_note.setText(prefix + (("\n\n" + detail) if detail else ""))
        elif mapped:
            self.result_note.setText("Result name verified by the legacy Grimoire + Focus mapping.")
        else:
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
        "texture": texture_for_scribed_skill(recipe.Grimoire, recipe.Focus),
        "scribing_recipe": recipe.to_dict(),
    }


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from widgets.build_editor import BuildEditor

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
