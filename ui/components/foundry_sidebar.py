# ==================================================
# Black Feather Foundry
# ui/components/foundry_sidebar.py
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
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
from services.accessibility_preferences import VISUAL_THEME_RYLO
from services.optional_modules import broadcast_enabled
from ui.theme.fonts import Fonts
from ui.ux_icons import icon_label, semantic_icon, set_button_icon


BROADCAST_NAV_SECTION = {"label": "Broadcast", "children": [
    ("Broadcast Desk", "broadcast"),
    ("Field Notes", "field_office"),
    ("Live Operations", "live_operations"),
    ("Archive", "archive"),
]}

CORE_NAV_SECTIONS = [
    ("Achievements", "achievements", "header"),
    {"label": "Collections", "page": "collectibles", "children": [
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


def nav_sections(include_broadcast: bool) -> list:
    if include_broadcast:
        return [BROADCAST_NAV_SECTION, *CORE_NAV_SECTIONS]
    return list(CORE_NAV_SECTIONS)


class FoundrySidebar(QWidget):
    pageRequested = Signal(str)

    def __init__(self, parent=None, include_broadcast: bool | None = None):
        super().__init__(parent)
        self.include_broadcast = broadcast_enabled() if include_broadcast is None else include_broadcast
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

    def _brand_mark_filename(self) -> str:
        app = QApplication.instance()
        if app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO:
            return "sidebar_scythe_rylo.svg"
        return "sidebar_feather_gold.svg"

    def refresh_brand_mark(self) -> None:
        if not hasattr(self, "brand_mark"):
            return
        pixmap = self._asset_pixmap(self._brand_mark_filename(), 30, 50)
        self.brand_mark.clear()
        if not pixmap.isNull():
            self.brand_mark.setPixmap(pixmap)
        else:
            self.brand_mark.setText("✦")

    def build_ui(self):
        self.setProperty("foundrySidebar", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        brand = QWidget()
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(6)

        self.brand_mark = QLabel()
        self.brand_mark.setFixedSize(36, 54)
        self.brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brand_mark.setProperty("sidebarBrandMark", True)
        self.refresh_brand_mark()
        brand_layout.addWidget(self.brand_mark, 0, Qt.AlignmentFlag.AlignTop)

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

        for section in nav_sections(self.include_broadcast):
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
        system_widgets = [self.archive, self.discord]
        if self.include_broadcast:
            system_widgets.insert(0, self.obs)
        for widget in system_widgets:
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
        plaque_layout.addWidget(icon_label("coffee", 18))
        plaque_text = QLabel("Field Office · Leave Better Records")
        plaque_text.setWordWrap(True)
        plaque_text.setProperty("sidebarFooter", True)
        plaque_layout.addWidget(plaque_text, 1)
        layout.addWidget(plaque)

    @staticmethod
    def divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setProperty("sidebarDivider", True)
        return line

    def build_leaf_button(self, text: str, page: str, header_style: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setProperty("nav", True)
        if header_style:
            button.setProperty("navHeader", True)
        icon_name = semantic_icon(text)
        if icon_name:
            set_button_icon(button, icon_name, 16)
        button.clicked.connect(lambda checked=False, p=page: self.pageRequested.emit(p))
        self.buttons[page] = button
        return button

    def build_category(self, section: dict) -> QWidget:
        wrapper = QWidget()
        wrapper.setProperty("navCategory", True)
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        label = QPushButton(section["label"])
        label.setCheckable(True)
        label.setChecked(True)
        label.setProperty("nav", True)
        label.setProperty("navCategoryHeader", True)
        icon_name = semantic_icon(section["label"])
        if icon_name:
            set_button_icon(label, icon_name, 16)
        if section.get("page"):
            label.clicked.connect(
                lambda checked=False, page=section["page"]: self.pageRequested.emit(page)
            )
        layout.addWidget(label)

        children = QWidget()
        children.setProperty("navChildren", True)
        child_layout = QVBoxLayout(children)
        child_layout.setContentsMargins(12, 0, 0, 0)
        child_layout.setSpacing(1)
        for text, page in section["children"]:
            child_layout.addWidget(self.build_leaf_button(text, page))
        layout.addWidget(children)
        label.toggled.connect(children.setVisible)
        return wrapper

    def set_current(self, page: str) -> None:
        for key, button in self.buttons.items():
            button.setChecked(key == page)

    def update_expedition_status(self, title: str, pulls: int, best_pull: str, coffee: str) -> None:
        self.current_boss.setText(title or "No Expedition")
        self.pull_count.setText(f"Pulls: {pulls}")
        self.best_pull.setText(f"Best: {best_pull or '--'}")
        self.coffee.setText(f"Coffee: {coffee or '--'}")

    def update_system_status(self, *, obs: str | None = None, archive: str | None = None, discord: str | None = None) -> None:
        if obs is not None and self.include_broadcast:
            self.obs.setText(f"● OBS · {obs}")
        if archive is not None:
            self.archive.setText(f"● Archive · {archive}")
        if discord is not None:
            self.discord.setText(f"● Discord · {discord}")
