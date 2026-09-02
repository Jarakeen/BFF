from __future__ import annotations

"""Small layout polish for the permanent Builds workspace.

Keep the working tab behavior intact while matching the Coverage tab treatment
and placing the Scribed Skill recipe editor before the saved-recipe list.
"""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    original_build_ui = BuildsPage._build_ui

    def build_ui_with_coverage_style_tabs(self) -> None:
        original_build_ui(self)

        # Coverage uses a normal QTabWidget. Match that instead of document mode,
        # which draws the long continuation line across the remaining tab bar.
        self.build_tabs.setDocumentMode(False)

        scribed_tab = self.build_tabs.widget(3)
        scribed_layout = scribed_tab.layout()
        recipe_editor = getattr(self, "scribed_recipe_editor", None)
        recipe_list = getattr(self, "scribed_skill_choices", None)
        if recipe_editor is not None and recipe_list is not None:
            # Workflow order: choose build -> create/edit recipe -> saved recipes.
            # The recipe editor was previously inserted after the expanding list,
            # which pushed the useful controls below a large blank area.
            scribed_layout.removeWidget(recipe_editor)
            list_index = scribed_layout.indexOf(recipe_list)
            scribed_layout.insertWidget(max(0, list_index), recipe_editor)

    BuildsPage._build_ui = build_ui_with_coverage_style_tabs
    _INSTALLED = True
