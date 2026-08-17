# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_sidebar.py
#
# Purpose:
# Primary navigation and status panel.
#
# Top-level sections can either be a single clickable
# page, or an expandable/collapsible category with child
# pages underneath it. Expanding/collapsing a category
# never adds height beyond its own children -- collapsed
# categories take up a single row, same as before.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QFrame,
    QScrollArea,
    QSizePolicy,
)

from ui.theme.fonts import Fonts


# --------------------------------------------------
# Navigation structure
#
# A section is either:
#   ("Label", "page_key")                        -> a leaf button
#   {"label": "Label", "children": [...]}         -> an expandable category
#
# A category's children are a list of either:
#   ("Label", "page_key")                         -> a child button
#   {"heading": "GROUP NAME"}                     -> a small visual
#                                                     divider, not a
#                                                     navigation level
# --------------------------------------------------

NAV_SECTIONS = [

    {
        "label": "Broadcast",
        "children": [
            ("Broadcast Desk", "broadcast"),
            ("Field Notes", "field_office"),
            ("Live Operations", "live_operations"),
            ("Archive", "archive"),
            ("Incident Reports", "incident"),
            # ("Achievement Desk", "achievement"),
            
        ],
    },


    ("Achievements", "collections", "header"),

    {
        "label": "Collections",
        "children": [
            ("Mounts", "collectibles:Mounts"),
            ("Pets", "collectibles:Pets"),
            ("Allies / Assistants", "collectibles:Allies / Assistants"),
            ("Houses", "collectibles:Houses"),
            ("Costumes", "collectibles:Costumes"),
            ("Skins", "collectibles:Skins"),
            ("Polymorphs", "collectibles:Polymorphs"),
            ("Personalities", "collectibles:Personalities"),
            ("Hairstyles & Adornments", "collectibles:Hairstyles & Adornments"),
            ("Mementos", "collectibles:Mementos"),
            ("Emotes", "collectibles:Emotes"),
            ("Customized Actions", "collectibles:Customized Actions"),
        ],
    },

    {
        "label": "Raid Operations",
        "children": [
            ("Dashboard", "operations_console"),
            ("Raid", "console:1"),
            ("Builds", "console:2"),
            ("Capabilities", "console:3"),
            ("Boss Guide", "console:4"),
            ("Assignments", "roster_page"),
            ("Optimization", "console:6"),
            ("Progression", "console:7"),
            ("References", "console:8"),
        ],
    },

    ("Settings", "settings"),

]


class FoundrySidebar(QWidget):

    pageRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Every clickable nav button (leaf or child), keyed by
        # page key, so the active page can be highlighted.
        self.buttons = {}

        self.build_ui()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.setProperty(
            "foundrySidebar",
            True,
        )

        # --------------------------------------------------
        # Sidebar shell
        #
        # The logo and footer stay fixed. Everything between
        # them is allowed to scroll when the window gets short.
        # --------------------------------------------------

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            18,
            20,
            18,
            20,
        )

        layout.setSpacing(12)

        #
        # Logo
        #

        logo = QLabel(
            "BLACK FEATHER FOUNDRY"
        )

        logo.setFont(
            Fonts.logo()
        )

        logo.setProperty(
            "sidebarLogo",
            True,
        )

        # Never let the logo be vertically compressed.
        logo.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        logo.setMinimumHeight(
            logo.sizeHint().height()
        )

        layout.addWidget(logo)
        layout.addWidget(self.divider())

        #
        # Scrollable sidebar content
        #

        scroll = QScrollArea()

        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll.setWidgetResizable(True)

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        content = QWidget()

        content_layout = QVBoxLayout(content)

        content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        content_layout.setSpacing(4)

        #
        # Navigation
        #

        for section in NAV_SECTIONS:

            if isinstance(section, tuple):

                text, page = section[0], section[1]

                style = section[2] if len(section) > 2 else None

                content_layout.addWidget(
                    self.build_leaf_button(
                        text,
                        page,
                        header_style=(style == "header"),
                    )
                )

            else:

                content_layout.addWidget(
                    self.build_category(section)
                )

        content_layout.addSpacing(8)

        content_layout.addStretch()

        content_layout.addWidget(self.divider())

        #
        # Expedition
        #

        self.status_title = QLabel(
            "CURRENT EXPEDITION"
        )

        self.status_title.setProperty(
            "sidebarHeading",
            True,
        )

        content_layout.addWidget(
            self.status_title
        )

        self.current_boss = QLabel(
            "No Expedition"
        )

        self.pull_count = QLabel(
            "Pulls: 0"
        )

        self.best_pull = QLabel(
            "Best: --"
        )

        self.coffee = QLabel(
            "Coffee: --"
        )

        content_layout.addWidget(self.current_boss)
        content_layout.addWidget(self.pull_count)
        content_layout.addWidget(self.best_pull)
        content_layout.addWidget(self.coffee)

        content_layout.addWidget(self.divider())

        #
        # Systems
        #

        systems = QLabel(
            "SYSTEMS"
        )

        systems.setProperty(
            "sidebarHeading",
            True,
        )

        content_layout.addWidget(systems)

        self.obs = QLabel("● OBS")
        self.archive = QLabel("● Archive")
        self.discord = QLabel("● Discord")

        content_layout.addWidget(self.obs)
        content_layout.addWidget(self.archive)
        content_layout.addWidget(self.discord)

        scroll.setWidget(content)

        layout.addWidget(
            scroll,
            1,
        )

        #
        # Footer
        #
        # Kept outside the scroll area so the version number
        # can never disappear when the window is resized.
        #

        footer = QLabel(
            "Black Feather Foundry\\nv1.0"
        )

        footer.setProperty(
            "sidebarFooter",
            True,
        )

        footer.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        footer.setMinimumHeight(
            footer.sizeHint().height()
        )

        layout.addWidget(
            footer
        )

    # --------------------------------------------------
    # Navigation builders
    # --------------------------------------------------

    def build_leaf_button(self, text, page, header_style=False):
        """
        A single top-level button that navigates directly
        to a page -- no children, nothing to expand.

        header_style renders it bold/uppercase like the
        expandable category headers, for a standalone entry
        that should carry the same visual weight even though
        it has no children of its own.
        """

        button = self.make_nav_button(
            text.upper() if header_style else text,
            indent=False,
        )

        button.clicked.connect(
            lambda _, p=page: self.activate(p)
        )

        self.buttons[page] = button

        return button

    def build_category(self, section):
        """
        A compact expandable/collapsible top-level category.
        The header toggles its children; it does not itself
        navigate anywhere. Collapsed, it only takes the
        height of the header row.
        """

        wrapper = QWidget()

        wrapper_layout = QVBoxLayout(wrapper)

        wrapper_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        wrapper_layout.setSpacing(2)

        header = self.make_nav_button(
            "▸  " + section["label"].upper(),
            indent=False,
        )

        children_box = QWidget()

        children_layout = QVBoxLayout(children_box)

        # Indent children instead of adding a second visual
        # system -- keeps the same buttons/theme, just offset.
        children_layout.setContentsMargins(
            14,
            0,
            0,
            0,
        )

        children_layout.setSpacing(2)

        for child in section["children"]:

            if isinstance(child, dict):

                children_layout.addWidget(
                    self.build_group_heading(
                        child["heading"]
                    )
                )

                continue

            label, page = child

            child_button = self.make_nav_button(
                label,
                indent=True,
            )

            child_button.clicked.connect(
                lambda _, p=page: self.activate(p)
            )

            self.buttons[page] = child_button

            children_layout.addWidget(child_button)

        children_box.setVisible(False)

        def toggle(_checked=False):

            expanded = not children_box.isVisible()

            children_box.setVisible(expanded)

            header.setText(
                ("▾  " if expanded else "▸  ")
                + section["label"].upper()
            )

        header.clicked.connect(toggle)

        wrapper_layout.addWidget(header)
        wrapper_layout.addWidget(children_box)

        return wrapper

    def build_group_heading(self, text):
        """
        A small non-clickable divider inside an expanded
        category -- a visual grouping only, not another
        navigation level.
        """

        label = QLabel(
            text.upper()
        )

        label.setProperty(
            "sidebarHeading",
            True,
        )

        return label

    def make_nav_button(self, text, indent):

        button = QPushButton(text)

        button.setProperty(
            "nav",
            True,
        )

        button.setProperty(
            "sidebarButton",
            True,
        )

        button.setFont(
            Fonts.sidebar()
        )

        button.setCheckable(True)

        # Compact, consistent height regardless of section --
        # no giant buttons, many entries fit in the sidebar.
        button.setMinimumHeight(30 if indent else 34)

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        return button

    # --------------------------------------------------
    # Selection
    # --------------------------------------------------

    def activate(self, page):
        """
        Emit the navigation request and highlight the
        button that was clicked (and only that button).
        """

        for key, button in self.buttons.items():

            button.setChecked(key == page)

        self.pageRequested.emit(page)

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def divider(self):

        line = QFrame()

        line.setFrameShape(
            QFrame.Shape.HLine
        )

        line.setProperty(
            "sidebarDivider",
            True,
        )

        return line
