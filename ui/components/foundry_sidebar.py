# ==================================================
# Black Feather Foundry
# ui/components/foundry_sidebar.py
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_resource_path
from ui.theme.fonts import Fonts
from ui.ux_icons import icon_label, semantic_icon, set_button_icon


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
        self.setMinimumWidth(215)
        self.setMaximumWidth(248)
        self.build_ui()

    @staticmethod
    def _asset_pixmap(filename: str, width: int, height: int) -> QPixmap:
        path = get_resource_path("assets", "themes", "bff", "grimoire", "assets", filename)
        pixmap = QPixmap(str(path)) if path.exists() else QPixmap()
        if pixmap.isNull():
            return pixmap
        return pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def build_ui(self):
        self.setProperty("foundrySidebar", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        brand = QWidget()
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(6)

        feather = QLabel()
        feather.setFixedSize(34, 54)
        feather.setAlignment(Qt.AlignmentFlag.AlignCenter)
        feather.setProperty("sidebarFeather", True)
        feather_pixmap = self._asset_pixmap("feather_watermark.svg", 28, 50)
        if not feather_pixmap.isNull():
            feather.setPixmap(feather_pixmap)
        else:
            feather.setText("❧")
        brand_layout.addWidget(feather, 0, Qt.AlignmentFlag.AlignTop)

        brand_text = QVBoxLayout()
        brand_text.setContentsMargins(0, 0, 0, 0)
        brand_text.setSpacing(0)
        logo = QLabel("BLACK FEATHER\nFOUNDRY")
        logo.setFont(Fonts.logo())
        logo.setProperty("sidebarLogo", True)
        logo.setWordWrap(True)
        logo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        brand_text.addWidget(logo)
        office = QLabel("FIELD OFFICE")
        office.setProperty("sidebarOffice", True)
        brand_text.addWidget(office)
        brand_layout.addLayout(brand_text, 1)
        layout.addWidget(brand)
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

        plaque = QFrame()
        plaque.setProperty("parchment", True)
        plaque.setProperty("sidebarPlaque", True)
        plaque_layout = QHBoxLayout(plaque)
        plaque_layout.setContentsMargins(8, 6, 8, 6)
        plaque_layout.setSpacing(6)
        mark = icon_label("gears", 20)
        mark.setProperty("sidebarPlaqueMark", True)
        plaque_layout.addWidget(mark, 0, Qt.AlignmentFlag.AlignTop)
        plaque_text = QLabel("THE FOUNDRY\nLeave better records.")
        plaque_text.setProperty("sidebarPlaqueText", True)
        plaque_text.setWordWrap(True)
        plaque_layout.addWidget(plaque_text, 1)
        layout.addWidget(plaque)

    def build_leaf_button(self, text, page, header_style=False):
        display = text.upper() if header_style else text
        button = self.make_nav_button(display, indent=False, icon_name=semantic_icon(text))
        button.clicked.connect(lambda _, p=page: self.activate(p))
        self.buttons[page] = button
        return button

    def build_category(self, section):
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(1)

        label = section["label"]
        header = self.make_nav_button("▸  " + label.upper(), indent=False, icon_name=semantic_icon(label))
        children_box = QWidget()
        children_layout = QVBoxLayout(children_box)
        children_layout.setContentsMargins(9, 0, 0, 0)
        children_layout.setSpacing(1)

        for child_label, page in section["children"]:
            child_button = self.make_nav_button(child_label, indent=True, icon_name=semantic_icon(child_label))
            child_button.clicked.connect(lambda _, p=page: self.activate(p))
            self.buttons[page] = child_button
            children_layout.addWidget(child_button)

        children_box.setVisible(False)

        def toggle(_checked=False):
            expanded = not children_box.isVisible()
            children_box.setVisible(expanded)
            header.setText(("▾  " if expanded else "▸  ") + label.upper())

        header.clicked.connect(toggle)
        wrapper_layout.addWidget(header)
        wrapper_layout.addWidget(children_box)
        return wrapper

    def make_nav_button(self, text, indent, icon_name=""):
        button = QPushButton(text)
        button.setProperty("nav", True)
        button.setProperty("sidebarButton", True)
        button.setFont(Fonts.sidebar())
        button.setCheckable(True)
        button.setMinimumHeight(25 if indent else 29)
        button.setMaximumHeight(31 if indent else 33)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            set_button_icon(button, icon_name, 15 if indent else 16)
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
