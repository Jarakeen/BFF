from __future__ import annotations

"""Performance safeguards for the permanent Builds/Edit workspace.

The Build Editor is intentionally kept inside the existing application window
for photosensitive-user safety.  This layer keeps that safer architecture while
removing avoidable work from the heavy editor path:

* eligibility controls rebuild only when their context actually changes;
* skill icons are cached for the process lifetime;
* one Build Editor widget is reused across saved builds;
* build-specific synthetic scribed skills are refreshed before each load.
"""

from functools import lru_cache

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components import eligible_build_editor as eligible
    from ui.builds_page import BuildsPage
    from ui.build_editor_inline_compat import _force_dark_surface, _set_combo_index
    from ui.build_workspace_edit_fix import _identity_card_for
    from ui.scribing_support import _recipes_for, _synthetic_skill

    # ---- Skill-row rebuild deduplication ---------------------------------
    # EligibleSkillBarRow setters historically rebuilt all six selectors every
    # time they were called, even when the requested state was already active.
    # BuildEditor.load can call these setters repeatedly for the same build.
    original_set_affiliation = eligible.EligibleSkillBarRow.set_affiliation
    original_set_form = eligible.EligibleSkillBarRow.set_form
    original_set_class = eligible.EligibleSkillBarRow.set_class

    def set_affiliation_if_changed(self, *, vampire: bool = False, werewolf: bool = False):
        vampire = bool(vampire)
        werewolf = bool(werewolf)
        if self.vampire == vampire and self.werewolf == werewolf:
            return
        original_set_affiliation(self, vampire=vampire, werewolf=werewolf)

    def set_form_if_changed(self, form: str | None):
        value = (form or "").strip().casefold()
        normalized = value if value in {"vampire", "werewolf"} else None
        if self.transformed_form == normalized:
            return
        original_set_form(self, form)

    def set_class_if_changed(self, eso_class: str):
        value = eso_class or ""
        if self._selected_class == value:
            return
        original_set_class(self, value)

    eligible.EligibleSkillBarRow.set_affiliation = set_affiliation_if_changed
    eligible.EligibleSkillBarRow.set_form = set_form_if_changed
    eligible.EligibleSkillBarRow.set_class = set_class_if_changed

    # Rebuilding a skill bar asks for the same icon many times, once per combo.
    # The skill records themselves are dicts and therefore cannot be passed
    # directly to lru_cache. Cache by the stable texture string instead.
    original_icon_for_skill = eligible._icon_for_skill

    @lru_cache(maxsize=4096)
    def icon_for_texture(texture: str):
        return original_icon_for_skill({"texture": texture})

    def cached_icon_for_skill(skill: dict):
        texture = str(skill.get("texture", "") or "").strip()
        return icon_for_texture(texture)

    eligible._icon_for_skill = cached_icon_for_skill

    # ---- Persistent Edit widget ------------------------------------------
    def refresh_scribed_choices(editor, build) -> None:
        canonical = [
            skill
            for skill in list(getattr(editor, "skill_choices", []) or [])
            if not (isinstance(skill, dict) and "scribing_recipe" in skill)
        ]
        existing = {
            str(skill.get("name", "") or "").strip().casefold()
            for skill in canonical
            if isinstance(skill, dict)
        }
        for recipe in _recipes_for(build):
            if not recipe.ResultName or recipe.ResultName.casefold() in existing:
                continue
            canonical.append(_synthetic_skill(recipe))
            existing.add(recipe.ResultName.casefold())
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

        if hasattr(editor, "name"):
            editor.name.hide()
        for label in editor.findChildren(QLabel):
            if label.text().strip() == "Character Name":
                label.hide()
        identity_card = _identity_card_for(editor)
        if identity_card is not None:
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
        # Keep the already-dark tab responsive before any unavoidable first
        # construction work begins.
        QTimer.singleShot(0, lambda selected=index: show_persistent_editor(self, selected))

    BuildsPage._load_edit_tab = load_edit_tab_persistent
    _INSTALLED = True
