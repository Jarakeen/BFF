from __future__ import annotations

"""Targeted fixes for the permanent Builds workspace.

Only the Edit tab needs special handling: it previously nested a QScrollArea
inside FoundryPage's existing workspace scroll area. That produced two vertical
scroll owners, expensive relayouts, and sluggish tab changes. The editor now
uses the page's existing scroll surface, caches heavy editor widgets, and places
the saved-build selector inside the Identity card instead of in a detached row.

The Scribed Skills tab also reads the canonical configured recipe data rather
than scanning unrelated crafted-skill database rows.
"""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel, QListWidgetItem, QVBoxLayout, QWidget

from ui.scribing_support import _recipes_for

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

        # The old checkbox-style Scribed Skills tab was fed from the wrong DB
        # concept. Until the full inline recipe builder is folded into this tab,
        # show the canonical configured recipes and never silently save an empty
        # checkbox list over them.
        self.save_scribed_button.hide()

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

    def load_scribed_tab_from_recipes(self, index: int) -> None:
        if index < 0 or index >= len(self.roster.Members):
            return
        build = self.roster.Members[index]
        recipes = _recipes_for(build)
        self.scribed_skill_choices.clear()
        if not recipes:
            item = QListWidgetItem("No scribed skills configured for this build.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.scribed_skill_choices.addItem(item)
        else:
            for recipe in recipes:
                detail = recipe.recipe_text or "legacy result-name entry"
                self.scribed_skill_choices.addItem(
                    QListWidgetItem(f"{recipe.ResultName}\n    {detail}")
                )
        self._scribed_index = index
        _set_combo_index(self.scribed_build_selector, index)

    BuildsPage._build_ui = build_ui_without_nested_edit_scroll
    BuildsPage._load_edit_tab = load_edit_tab_single_scroll
    BuildsPage._load_scribed_tab = load_scribed_tab_from_recipes
    _INSTALLED = True
