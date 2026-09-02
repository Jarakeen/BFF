from __future__ import annotations

"""Targeted fixes for the permanent Builds workspace.

Only the Edit tab needs special handling: it previously nested a QScrollArea
inside FoundryPage's existing workspace scroll area. That produced two vertical
scroll owners, expensive relayouts, and sluggish tab changes. The editor now
uses the page's existing scroll surface, caches heavy editor widgets, and places
the saved-build selector inside the Identity card instead of in a detached row.

The Scribed Skills tab reads and edits the canonical configured recipe data
rather than scanning unrelated crafted-skill database rows.
"""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.scribing_recipe import ScribedSkillRecipe
from services.scribing_catalog import (
    compatible_affix,
    compatible_focus,
    compatible_signature,
    grimoire_names,
    result_name,
)
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.scribing_support import _recipes_for, _store_recipes

_INSTALLED = False


def _recipe_signature(build) -> tuple[tuple[str, str, str, str, str], ...]:
    return tuple(
        (
            recipe.ResultName.strip().casefold(),
            recipe.Grimoire.strip().casefold(),
            recipe.Focus.strip().casefold(),
            recipe.Signature.strip().casefold(),
            recipe.Affix.strip().casefold(),
        )
        for recipe in _recipes_for(build)
    )


def _identity_card_for(editor):
    widget = getattr(editor, "name", None)
    parent = widget.parentWidget() if widget is not None else None
    while parent is not None:
        title_label = getattr(parent, "title_label", None)
        if title_label is not None and title_label.text().strip() == "Identity":
            return parent
        parent = parent.parentWidget()
    return None


def _replace_combo(combo: QComboBox, values: list[str], current: str = "") -> None:
    combo.blockSignals(True)
    combo.clear()
    combo.addItem("")
    combo.addItems(values)
    if current and combo.findText(current, Qt.MatchFlag.MatchExactly) >= 0:
        combo.setCurrentText(current)
    combo.blockSignals(False)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from ui.build_editor_inline_compat import _force_dark_surface, _set_combo_index

    original_build_ui = BuildsPage._build_ui

    def build_ui_without_nested_edit_scroll(self) -> None:
        original_build_ui(self)

        edit_tab = self.build_tabs.widget(1)
        edit_layout = edit_tab.layout()

        # Remove the detached selector row. Keep the combo alive so it can be
        # placed directly in the active editor's Identity card.
        selector_row_item = edit_layout.takeAt(0)
        selector_row = selector_row_item.layout() if selector_row_item is not None else None
        if selector_row is not None:
            while selector_row.count():
                item = selector_row.takeAt(0)
                widget = item.widget()
                if widget is self.edit_build_selector:
                    widget.setParent(edit_tab)
                    widget.hide()
                elif widget is not None:
                    widget.deleteLater()

        # Remove Edit's private QScrollArea. FoundryPage already owns the page
        # scroll surface, so a second one only creates competing scroll ranges.
        old_scroll = self.edit_build_scroll
        edit_layout.removeWidget(old_scroll)
        old_child = old_scroll.takeWidget()
        if old_child is not None:
            old_child.deleteLater()
        old_scroll.deleteLater()
        self.edit_build_scroll = None

        self.edit_build_host = QWidget(edit_tab)
        _force_dark_surface(self.edit_build_host)
        host_layout = QVBoxLayout(self.edit_build_host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)
        loading = QLabel("Select a saved build from Roster or the Character Name list.")
        loading.setObjectName("editBuildLoadingLabel")
        host_layout.addWidget(loading)
        host_layout.addStretch()
        edit_layout.addWidget(self.edit_build_host, 1)

        self._build_editor_cache = {}
        self._build_editor = None
        self._build_editor_index = None
        self._pending_edit_index = None

        # Replace the old checkbox-style Scribed Skills controls with an inline
        # recipe builder using the canonical Grimoire/Focus/Signature/Affix
        # representation. No native dialog is needed.
        self.save_scribed_button.hide()
        scribed_tab = self.build_tabs.widget(3)
        scribed_layout = scribed_tab.layout()

        recipe_editor = QWidget(scribed_tab)
        recipe_editor.setObjectName("scribedRecipeEditor")
        _force_dark_surface(recipe_editor)
        recipe_root = QVBoxLayout(recipe_editor)
        recipe_root.setContentsMargins(0, 6, 0, 0)
        recipe_root.setSpacing(6)

        recipe_form = QFormLayout()
        self.scribed_grimoire = QComboBox(recipe_editor)
        self.scribed_grimoire.addItem("")
        self.scribed_grimoire.addItems(grimoire_names())
        self.scribed_focus = QComboBox(recipe_editor)
        self.scribed_signature = QComboBox(recipe_editor)
        self.scribed_affix = QComboBox(recipe_editor)
        self.scribed_result = QLineEdit(recipe_editor)
        self.scribed_result.setPlaceholderText("Exact in-game skill name")
        recipe_form.addRow("Grimoire", self.scribed_grimoire)
        recipe_form.addRow("Focus", self.scribed_focus)
        recipe_form.addRow("Signature", self.scribed_signature)
        recipe_form.addRow("Affix", self.scribed_affix)
        recipe_form.addRow("Result Skill", self.scribed_result)
        recipe_root.addLayout(recipe_form)

        self.scribed_recipe_note = QLabel(recipe_editor)
        self.scribed_recipe_note.setWordWrap(True)
        recipe_root.addWidget(self.scribed_recipe_note)

        recipe_actions = QHBoxLayout()
        self.new_scribed_recipe_button = FoundryButton(
            "+ New Scribed Skill", role=ButtonRole.SECONDARY, compact=True
        )
        self.save_scribed_recipe_button = FoundryButton(
            "Save Scribed Skill", role=ButtonRole.SUCCESS, compact=True
        )
        self.remove_scribed_recipe_button = FoundryButton(
            "Remove", role=ButtonRole.DANGER, compact=True
        )
        recipe_actions.addWidget(self.new_scribed_recipe_button)
        recipe_actions.addStretch()
        recipe_actions.addWidget(self.remove_scribed_recipe_button)
        recipe_actions.addWidget(self.save_scribed_recipe_button)
        recipe_root.addLayout(recipe_actions)

        # Insert directly after the recipe list and before the old action row.
        scribed_layout.insertWidget(3, recipe_editor)
        self.scribed_recipe_editor = recipe_editor
        self._scribed_recipes: list[ScribedSkillRecipe] = []
        self._scribed_recipe_row = -1

        self.scribed_grimoire.currentTextChanged.connect(
            lambda *_: self._refresh_scribed_recipe_options()
        )
        self.scribed_focus.currentTextChanged.connect(
            lambda *_: self._refresh_scribed_result_name()
        )
        self.scribed_skill_choices.currentRowChanged.connect(
            lambda row: self._select_scribed_recipe(row)
        )
        self.new_scribed_recipe_button.clicked.connect(
            lambda *_: self._clear_scribed_recipe_form()
        )
        self.save_scribed_recipe_button.clicked.connect(
            lambda *_: self._save_scribed_recipe_form()
        )
        self.remove_scribed_recipe_button.clicked.connect(
            lambda *_: self._remove_scribed_recipe()
        )

    def _show_editor(self, index: int) -> None:
        self._pending_edit_index = None
        if self.build_tabs.currentIndex() != 1:
            return
        if index < 0 or index >= len(self.roster.Members):
            return

        build = self.roster.Members[index]
        signature = _recipe_signature(build)
        editor = self._build_editor_cache.get(signature)
        if editor is None:
            editor = self._editor(build)
            _force_dark_surface(editor)
            editor.saveRequested.connect(lambda: self._save_edit_tab())
            editor.cancelRequested.connect(lambda: self._cancel_edit_tab())
            self._build_editor_cache[signature] = editor
            self.edit_build_host.layout().insertWidget(0, editor, 1)
        editor.load(build)

        # Hide every cached editor except the one currently in use.
        for cached in self._build_editor_cache.values():
            cached.setVisible(cached is editor)

        # The dropdown now occupies the Identity card itself. The original
        # character-name line edit remains hidden model state so save semantics
        # remain unchanged.
        if hasattr(editor, "name"):
            editor.name.hide()
        for label in editor.findChildren(QLabel):
            if label.text().strip() == "Character Name":
                label.hide()
        identity_card = _identity_card_for(editor)
        if identity_card is not None:
            self.edit_build_selector.show()
            identity_card.set_header_action(self.edit_build_selector)

        # Remove the one-time placeholder once an editor exists.
        placeholder = self.edit_build_host.findChild(QLabel, "editBuildLoadingLabel")
        if placeholder is not None:
            placeholder.hide()

        self._build_editor = editor
        self._build_editor_index = index
        _set_combo_index(self.edit_build_selector, index)

    def load_edit_tab_single_scroll(self, index: int) -> None:
        if index < 0 or index >= len(self.roster.Members):
            return
        if self._build_editor is not None and self._build_editor_index == index:
            _set_combo_index(self.edit_build_selector, index)
            return
        if self._pending_edit_index == index:
            return

        self._pending_edit_index = index
        # Let Qt paint the already-dark Edit tab first, then do the expensive
        # editor construction. This prevents the tab click itself from waiting
        # on hundreds of child controls before anything appears onscreen.
        QTimer.singleShot(0, lambda selected=index: _show_editor(self, selected))

    def clear_scribed_recipe_form(self) -> None:
        self._scribed_recipe_row = -1
        self.scribed_skill_choices.blockSignals(True)
        self.scribed_skill_choices.setCurrentRow(-1)
        self.scribed_skill_choices.blockSignals(False)
        self.scribed_grimoire.setCurrentIndex(0)
        _replace_combo(self.scribed_focus, [])
        _replace_combo(self.scribed_signature, [])
        _replace_combo(self.scribed_affix, [])
        self.scribed_result.clear()
        self.scribed_recipe_note.setText("Choose a Grimoire to begin a new scribed skill.")

    def refresh_scribed_recipe_options(self) -> None:
        grimoire = self.scribed_grimoire.currentText().strip()
        old_focus = self.scribed_focus.currentText().strip()
        old_signature = self.scribed_signature.currentText().strip()
        old_affix = self.scribed_affix.currentText().strip()
        _replace_combo(self.scribed_focus, compatible_focus(grimoire), old_focus)
        _replace_combo(self.scribed_signature, compatible_signature(grimoire), old_signature)
        _replace_combo(self.scribed_affix, compatible_affix(grimoire), old_affix)
        self._refresh_scribed_result_name()

    def refresh_scribed_result_name(self) -> None:
        mapped = result_name(
            self.scribed_grimoire.currentText(), self.scribed_focus.currentText()
        )
        if mapped:
            self.scribed_result.setText(mapped)
            self.scribed_recipe_note.setText(
                "Result name verified for this Grimoire + Focus pair."
            )
        else:
            if self.scribed_focus.currentText().strip():
                self.scribed_recipe_note.setText(
                    "This Grimoire + Focus result name is not normalized yet. "
                    "Enter the exact name shown in ESO; the recipe will still be preserved."
                )
            else:
                self.scribed_recipe_note.setText("Choose a Focus script to resolve the result skill.")

    def select_scribed_recipe(self, row: int) -> None:
        if row < 0 or row >= len(self._scribed_recipes):
            return
        recipe = self._scribed_recipes[row]
        self._scribed_recipe_row = row
        self.scribed_grimoire.blockSignals(True)
        self.scribed_grimoire.setCurrentText(recipe.Grimoire)
        self.scribed_grimoire.blockSignals(False)
        _replace_combo(self.scribed_focus, compatible_focus(recipe.Grimoire), recipe.Focus)
        _replace_combo(
            self.scribed_signature,
            compatible_signature(recipe.Grimoire),
            recipe.Signature,
        )
        _replace_combo(self.scribed_affix, compatible_affix(recipe.Grimoire), recipe.Affix)
        self.scribed_result.setText(recipe.ResultName)
        self.scribed_recipe_note.setText("Editing the selected configured scribed skill.")

    def save_scribed_recipe_form(self) -> None:
        index = self._scribed_index
        if index is None or index < 0 or index >= len(self.roster.Members):
            self.status.error("Choose a saved build before adding a scribed skill.")
            return

        values = {
            "Grimoire": self.scribed_grimoire.currentText().strip(),
            "Focus": self.scribed_focus.currentText().strip(),
            "Signature": self.scribed_signature.currentText().strip(),
            "Affix": self.scribed_affix.currentText().strip(),
            "Result Skill": self.scribed_result.text().strip(),
        }
        missing = [label for label, value in values.items() if not value]
        if missing:
            self.status.error("Complete the scribed skill: " + ", ".join(missing))
            return

        recipe = ScribedSkillRecipe(
            ResultName=values["Result Skill"],
            Grimoire=values["Grimoire"],
            Focus=values["Focus"],
            Signature=values["Signature"],
            Affix=values["Affix"],
        )
        recipes = list(self._scribed_recipes)
        row = self._scribed_recipe_row
        if 0 <= row < len(recipes):
            recipes[row] = recipe
        else:
            recipes.append(recipe)
            row = len(recipes) - 1

        build = self.roster.Members[index]
        _store_recipes(build, recipes)
        self.selected_index = index
        self._save()
        self._load_scribed_tab(index)
        if 0 <= row < self.scribed_skill_choices.count():
            self.scribed_skill_choices.setCurrentRow(row)
        self.status.success(f"Saved scribed skill: {recipe.ResultName}.")

        # Scribed recipes change which synthetic skills are available in Edit.
        # Force a fresh editor selection the next time Edit is activated.
        if self._build_editor_index == index:
            self._build_editor = None
            self._build_editor_index = None

    def remove_scribed_recipe(self) -> None:
        index = self._scribed_index
        row = self._scribed_recipe_row
        if index is None or index < 0 or index >= len(self.roster.Members):
            return
        if row < 0 or row >= len(self._scribed_recipes):
            self.status.error("Select a scribed skill to remove.")
            return
        recipes = list(self._scribed_recipes)
        removed = recipes.pop(row)
        _store_recipes(self.roster.Members[index], recipes)
        self.selected_index = index
        self._save()
        self._load_scribed_tab(index)
        self._clear_scribed_recipe_form()
        self.status.success(f"Removed scribed skill: {removed.ResultName}.")
        if self._build_editor_index == index:
            self._build_editor = None
            self._build_editor_index = None

    def load_scribed_tab_from_recipes(self, index: int) -> None:
        if index < 0 or index >= len(self.roster.Members):
            return
        build = self.roster.Members[index]
        recipes = list(_recipes_for(build))
        self._scribed_recipes = recipes
        self.scribed_skill_choices.blockSignals(True)
        self.scribed_skill_choices.clear()
        if not recipes:
            item = QListWidgetItem("No scribed skills configured for this build yet.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.scribed_skill_choices.addItem(item)
        else:
            for recipe in recipes:
                detail = recipe.recipe_text or "legacy result-name entry"
                self.scribed_skill_choices.addItem(
                    QListWidgetItem(f"{recipe.ResultName}\n    {detail}")
                )
        self.scribed_skill_choices.blockSignals(False)
        self._scribed_index = index
        self._scribed_recipe_row = -1
        _set_combo_index(self.scribed_build_selector, index)
        self._clear_scribed_recipe_form()

    BuildsPage._build_ui = build_ui_without_nested_edit_scroll
    BuildsPage._load_edit_tab = load_edit_tab_single_scroll
    BuildsPage._load_scribed_tab = load_scribed_tab_from_recipes
    BuildsPage._clear_scribed_recipe_form = clear_scribed_recipe_form
    BuildsPage._refresh_scribed_recipe_options = refresh_scribed_recipe_options
    BuildsPage._refresh_scribed_result_name = refresh_scribed_result_name
    BuildsPage._select_scribed_recipe = select_scribed_recipe
    BuildsPage._save_scribed_recipe_form = save_scribed_recipe_form
    BuildsPage._remove_scribed_recipe = remove_scribed_recipe
    _INSTALLED = True
