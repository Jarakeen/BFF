from __future__ import annotations

"""Place Scribing where builds are authored instead of exposing a duplicate tool page.

The canonical recipe editor and persistence live in ``ui.scribing_support``.  This
startup layer only embeds that existing workflow in BuildEditor, refreshes configured
scribed skills into the live skill selectors, and removes the old standalone Tools
navigation route.
"""

_INSTALLED = False


def _remove_standalone_navigation() -> None:
    from ui.components import foundry_sidebar

    for section in foundry_sidebar.CORE_NAV_SECTIONS:
        if not isinstance(section, dict):
            continue
        children = section.get("children")
        if not isinstance(children, list):
            continue
        section["children"] = [
            route
            for route in children
            if not (
                isinstance(route, (tuple, list))
                and len(route) >= 2
                and str(route[1]).strip() == "scribing_simulator"
            )
        ]


def _refresh_editor_skill_choices(editor) -> None:
    """Recompose the live editor skill catalog from its configured recipes."""

    from ui.scribing_editor_compat import _configured_skill

    recipes = list(getattr(editor, "_scribed_skill_recipes", []) or [])
    base_choices = [
        skill
        for skill in list(getattr(editor, "skill_choices", []) or [])
        if not (isinstance(skill, dict) and skill.get("scribing_recipe"))
    ]
    existing = {
        str(skill.get("name", "")).strip().casefold()
        for skill in base_choices
        if isinstance(skill, dict) and str(skill.get("name", "")).strip()
    }
    for recipe in recipes:
        name = str(getattr(recipe, "ResultName", "") or "").strip()
        if not name or name.casefold() in existing:
            continue
        base_choices.append(_configured_skill(recipe))
        existing.add(name.casefold())

    editor.skill_choices[:] = base_choices
    eso_class = editor.eso_class.currentText().strip() if hasattr(editor, "eso_class") else ""
    rows = []
    for name in ("front_bar", "back_bar"):
        row = getattr(editor, name, None)
        if row is not None:
            rows.append(row)
    for card in list(getattr(editor, "_boss_cards", []) or []):
        rows.extend((card.front_bar, card.back_bar))

    for row in rows:
        row.all_skill_choices = editor.skill_choices
        row.set_class(eso_class)


def _refresh_editor_summary(editor) -> None:
    label = getattr(editor, "_scribed_skills_summary", None)
    if label is None:
        return
    names = [
        str(getattr(recipe, "ResultName", "") or "").strip()
        for recipe in list(getattr(editor, "_scribed_skill_recipes", []) or [])
        if str(getattr(recipe, "ResultName", "") or "").strip()
    ]
    if not names:
        label.setText("No scribed skills configured for this build.")
        return
    label.setText("Configured: " + " • ".join(names))


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    _remove_standalone_navigation()

    from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel

    from ui.components.foundry_button import ButtonRole, FoundryButton
    from ui.scribing_support import ScribedSkillsDialog
    from widgets.build_editor import BuildEditor

    original_build_skills_card = BuildEditor._build_skills_card
    original_load = BuildEditor.load

    def build_skills_card_with_scribing(self):
        card = original_build_skills_card(self)
        row = QHBoxLayout()
        heading = QLabel("Scribed Skills")
        heading.setStyleSheet("font-weight:700;")
        self._scribed_skills_summary = QLabel("No scribed skills configured for this build.")
        self._scribed_skills_summary.setWordWrap(True)
        button = FoundryButton(
            "Build / Edit Scribed Skills",
            role=ButtonRole.SECONDARY,
            compact=True,
        )
        button.clicked.connect(self._edit_scribed_skills_in_builder)
        row.addWidget(heading)
        row.addWidget(self._scribed_skills_summary, 1)
        row.addWidget(button)
        card.addLayout(row)
        return card

    def edit_scribed_skills_in_builder(self) -> None:
        dialog = ScribedSkillsDialog(
            list(getattr(self, "_scribed_skill_recipes", []) or []),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._scribed_skill_recipes = dialog.recipes
        _refresh_editor_skill_choices(self)
        _refresh_editor_summary(self)

    def load_with_scribing_section(self, model) -> None:
        original_load(self, model)
        _refresh_editor_skill_choices(self)
        # A direct BuildEditor construction may not have had saved synthetic skills
        # available during the first load. Reapply the saved bars after recomposition.
        self.front_bar.load(model.FrontBarSkills)
        self.back_bar.load(model.BackBarSkills)
        for card, loadout in zip(self._boss_cards, model.BossLoadouts):
            card.load(loadout)
        _refresh_editor_summary(self)

    BuildEditor._build_skills_card = build_skills_card_with_scribing
    BuildEditor._edit_scribed_skills_in_builder = edit_scribed_skills_in_builder
    BuildEditor.load = load_with_scribing_section

    _INSTALLED = True
