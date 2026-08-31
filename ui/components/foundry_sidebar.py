# ==================================================
# Black Feather Foundry
# ui/components/foundry_sidebar.py
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from ui.theme.fonts import Fonts


NAV_SECTIONS = [
    {"label": "Broadcast", "children": [
        ("Broadcast Desk", "broadcast"),
        ("Field Notes", "field_office"),
        ("Live Operations", "live_operations"),
        ("Archive", "archive"),
    ]},
    ("Achievements", "achievements", "header"),
    {"label": "Collections", "children": [
        ("Mounts", "collectibles:Mounts"), ("Pets", "collectibles:Pets"),
        ("Allies / Assistants", "collectibles:Allies / Assistants"), ("Houses", "collectibles:Houses"),
        ("Costumes", "collectibles:Costumes"), ("Skins", "collectibles:Skins"),
        ("Polymorphs", "collectibles:Polymorphs"), ("Personalities", "collectibles:Personalities"),
        ("Hairstyles & Adornments", "collectibles:Hairstyles & Adornments"), ("Mementos", "collectibles:Mementos"),
        ("Emotes", "collectibles:Emotes"), ("Customized Actions", "collectibles:Customized Actions"),
        ("Weapon Styles", "collectibles:Weapon Styles"), ("Armor Styles", "collectibles:Armor Styles"),
        ("Furnishings", "collectibles:Furnishings"), ("Fragments", "collectibles:Fragments"),
        ("Tools & Upgrades", "collectibles:Tools & Upgrades"),
    ]},
    {"label": "Raid Engine", "children": [
        ("Overview", "operations_console"), ("Encounters", "console:1"), ("Builds", "console:2"),
        ("Performance", "console:3"), ("Mechanics", "console:4"), ("Assignments", "roster_page"),
        ("Optimization", "console:6"), ("Coverage", "console:7"), ("Reference Data", "console:8"),
    ]},
    ("Settings", "settings"),
]


class FoundrySidebar(QWidget):
    pageRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons = {}
        self.setMinimumWidth(205)
        self.setMaximumWidth(235)
        self.build_ui()

    def build_ui(self):
        self.setProperty("foundrySidebar", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(7)

        logo = QLabel("BLACK FEATHER FOUNDRY")
        logo.setFont(Fonts.logo())
        logo.setProperty("sidebarLogo", True)
        logo.setWordWrap(True)
        logo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(logo)

        office = QLabel("FIELD OFFICE")
        office.setProperty("sidebarOffice", True)
        layout.addWidget(office)
        layout.addWidget(self.divider())

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)

        for section in NAV_SECTIONS:
            if isinstance(section, tuple):
                text, page = section[0], section[1]
                style = section[2] if len(section) > 2 else None
                content_layout.addWidget(self.build_leaf_button(text, page, header_style=(style == "header")))
            else:
                content_layout.addWidget(self.build_category(section))

        content_layout.addSpacing(5)
        content_layout.addStretch()
        content_layout.addWidget(self.divider())

        self.status_title = QLabel("CURRENT EXPEDITION")
        self.status_title.setProperty("sidebarHeading", True)
        content_layout.addWidget(self.status_title)
        self.current_boss = QLabel("No Expedition")
        self.pull_count = QLabel("Pulls: 0")
        self.best_pull = QLabel("Best: --")
        self.coffee = QLabel("Coffee: --")
        for widget in (self.current_boss, self.pull_count, self.best_pull, self.coffee):
            widget.setProperty("sidebarMeta", True)
            content_layout.addWidget(widget)

        content_layout.addWidget(self.divider())
        systems = QLabel("SYSTEMS")
        systems.setProperty("sidebarHeading", True)
        content_layout.addWidget(systems)
        self.obs = QLabel("● OBS")
        self.archive = QLabel("● Archive")
        self.discord = QLabel("● Discord")
        for widget in (self.obs, self.archive, self.discord):
            widget.setProperty("sidebarMeta", True)
            content_layout.addWidget(widget)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        footer = QLabel("BLACK FEATHER FOUNDRY\nField records remain open.")
        footer.setProperty("sidebarFooter", True)
        footer.setWordWrap(True)
        footer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(footer)

    def build_leaf_button(self, text, page, header_style=False):
        button = self.make_nav_button(text.upper() if header_style else text, indent=False)
        button.clicked.connect(lambda _, p=page: self.activate(p))
        self.buttons[page] = button
        return button

    def build_category(self, section):
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(1)

        header = self.make_nav_button("▸  " + section["label"].upper(), indent=False)
        children_box = QWidget()
        children_layout = QVBoxLayout(children_box)
        children_layout.setContentsMargins(9, 0, 0, 0)
        children_layout.setSpacing(1)

        for label, page in section["children"]:
            child_button = self.make_nav_button(label, indent=True)
            child_button.clicked.connect(lambda _, p=page: self.activate(p))
            self.buttons[page] = child_button
            children_layout.addWidget(child_button)

        children_box.setVisible(False)

        def toggle(_checked=False):
            expanded = not children_box.isVisible()
            children_box.setVisible(expanded)
            header.setText(("▾  " if expanded else "▸  ") + section["label"].upper())

        header.clicked.connect(toggle)
        wrapper_layout.addWidget(header)
        wrapper_layout.addWidget(children_box)
        return wrapper

    def make_nav_button(self, text, indent):
        button = QPushButton(text)
        button.setProperty("nav", True)
        button.setProperty("sidebarButton", True)
        button.setFont(Fonts.sidebar())
        button.setCheckable(True)
        button.setMinimumHeight(24 if indent else 28)
        button.setMaximumHeight(30 if indent else 32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def activate(self, page):
        for key, button in self.buttons.items():
            button.setChecked(key == page)
        self.pageRequested.emit(page)

    def divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setProperty("sidebarDivider", True)
        return line
