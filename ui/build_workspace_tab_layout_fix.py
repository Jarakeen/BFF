from __future__ import annotations

"""Small layout polish for permanent workspaces and shared tab geometry.

Builds keeps the working tab behavior intact while matching the Coverage tab
treatment. Theme application also gets one shared file-folder tab rule so every
visual theme receives rounded top corners and square bottom corners.
"""

_INSTALLED = False

_ROUNDED_TAB_STYLE = """
QTabBar::tab {
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}
"""


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from ui.theme import ThemeManager

    original_build_ui = BuildsPage._build_ui
    original_theme_apply = ThemeManager.apply

    def apply_with_rounded_tabs(self, app) -> None:
        original_theme_apply(self, app)
        stylesheet = app.styleSheet()
        if _ROUNDED_TAB_STYLE.strip() not in stylesheet:
            app.setStyleSheet(stylesheet + "\n" + _ROUNDED_TAB_STYLE)

    def build_ui_with_coverage_style_tabs(self) -> None:
        original_build_ui(self)

        # Coverage uses a normal QTabWidget. Match that instead of document mode,
        # which draws the long continuation line across the remaining tab bar.
        self.build_tabs.setDocumentMode(False)

        # The left workspace is saved character/build data, not the raid team
        # roster. Use labels that describe what users are actually looking at.
        self.build_tabs.setTabText(0, "Builds")
        roster_card = self.splitter.widget(0)
        if hasattr(roster_card, "set_title"):
            roster_card.set_title("Character Builds")

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

    ThemeManager.apply = apply_with_rounded_tabs
    BuildsPage._build_ui = build_ui_with_coverage_style_tabs
    _INSTALLED = True
