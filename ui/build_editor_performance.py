from __future__ import annotations

"""Performance safeguards for the permanent Builds/Edit workspace.

The Build Editor is intentionally kept inside the existing application window
for photosensitive-user safety. This layer keeps the safer architecture while
removing the largest avoidable cost from the Edit tab:

* one Build Editor widget is reused across saved builds;
* build-specific synthetic scribed skills are refreshed before each load.

Skill-bar eligibility setters and icon resolution intentionally remain on their
canonical implementations. Earlier attempts to monkeypatch those hot paths
caused skill-bar population regressions, so correctness wins there.
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from ui.build_editor_inline_compat import _force_dark_surface, _set_combo_index
    from ui.build_workspace_edit_fix import _identity_card_for
    from ui.scribing_editor_compat import _configured_skill
    from ui.scribing_support import _recipes_for

    # ---- Persistent Edit widget ------------------------------------------
    def refresh_scribed_choices(editor, build) -> None:
        selected_names = {
            str(name or "").strip().casefold()
            for name in getattr(build, "ScribedSkills", [])
            if str(name or "").strip()
        }
        recipes = list(_recipes_for(build))

        def complete_recipe(recipe) -> bool:
            return all(
                str(getattr(recipe, field, "") or "").strip()
                for field in ("ResultName", "Grimoire", "Focus", "Signature", "Affix")
            )

        configured = [recipe for recipe in recipes if complete_recipe(recipe)]
        configured_names = {recipe.ResultName.strip().casefold() for recipe in configured}

        canonical = []
        for original in list(getattr(editor, "skill_choices", []) or []):
            if not isinstance(original, dict):
                canonical.append(original)
                continue
            # Synthetic/configured choices and earlier editor-only copies are
            # rebuilt for the currently selected saved build.
            if "scribing_recipe" in original or original.get("editor_selectable_scribed"):
                continue
            name = str(original.get("name", "") or "").strip().casefold()
            crafted = int(original.get("is_crafted") or 0) == 1
            if crafted and name in configured_names:
                # Prefer the configured synthetic form below. It has a stable
                # synthetic ID and complete recipe semantics.
                continue
            if crafted and name in selected_names:
                selectable = dict(original)
                selectable["editor_selectable_scribed"] = True
                canonical.append(selectable)
            else:
                canonical.append(original)

        existing = {
            str(skill.get("name", "") or "").strip().casefold()
            for skill in canonical
            if isinstance(skill, dict)
        }
        for recipe in configured:
            name = recipe.ResultName.strip()
            if not name or name.casefold() in existing:
                continue
            canonical.append(_configured_skill(recipe))
            existing.add(name.casefold())

        editor.skill_choices = canonical
        for row in (getattr(editor, "front_bar", None), getattr(editor, "back_bar", None)):
            if row is not None:
                row.all_skill_choices = editor.skill_choices

    def show_persistent_editor(self, index: int) -> None:
        self._pending_edit_index = None
        if self.build_tabs.currentIndex() != 1:
            return
        if index < 0 or index >= len(self.roster.Members):
            return

        build = self.roster.Members[index]
        editor = getattr(self, "_persistent_build_editor", None)
        if editor is None:
            editor = self._editor(build)
            _force_dark_surface(editor)
            editor.saveRequested.connect(lambda: self._save_edit_tab())
            editor.cancelRequested.connect(lambda: self._cancel_edit_tab())
            self.edit_build_host.layout().insertWidget(0, editor, 1)
            self._persistent_build_editor = editor

        refresh_scribed_choices(editor, build)
        editor.setUpdatesEnabled(False)
        try:
            editor.load(build)
        finally:
            editor.setUpdatesEnabled(True)
            editor.update()

        # The Identity card must expose the real PlayerBuild.Name field. The
        # header dropdown is only a saved-build selector and must never replace
        # or masquerade as editable character identity.
        if hasattr(editor, "name"):
            editor.name.show()
        for label in editor.findChildren(QLabel):
            if label.text().strip() == "Character Name":
                label.show()
        identity_card = _identity_card_for(editor)
        if identity_card is not None:
            self.edit_build_selector.setToolTip("Select saved build")
            self.edit_build_selector.show()
            identity_card.set_header_action(self.edit_build_selector)

        placeholder = self.edit_build_host.findChild(QLabel, "editBuildLoadingLabel")
        if placeholder is not None:
            placeholder.hide()

        self._build_editor = editor
        self._build_editor_index = index
        _set_combo_index(self.edit_build_selector, index)

    def load_edit_tab_persistent(self, index: int) -> None:
        if index < 0 or index >= len(self.roster.Members):
            return
        if self._build_editor is not None and self._build_editor_index == index:
            _set_combo_index(self.edit_build_selector, index)
            return
        if self._pending_edit_index == index:
            return
        self._pending_edit_index = index
        # Paint the already-dark Edit tab before the unavoidable first editor
        # construction begins. Later visits reuse the same widget.
        QTimer.singleShot(0, lambda selected=index: show_persistent_editor(self, selected))

    BuildsPage._load_edit_tab = load_edit_tab_persistent
    _INSTALLED = True