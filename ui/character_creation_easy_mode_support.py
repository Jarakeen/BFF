from __future__ import annotations

"""Inline, inviting front-door character/build creation for the Builds workspace.

The creation flow lives at the top of Builds instead of in a modal window. It
keeps the existing canonical CharacterCreationService and only changes how the
user enters the required identity/build basics.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from models.roster_model import ESO_CLASSES
from services.character_creation_service import (
    CharacterCreationRequest,
    CharacterCreationService,
)
from services.gear_set_armor_weight_resolver import GearSetArmorWeightResolver
from ui.components.foundry_button import ButtonRole, FoundryButton

_INSTALLED = False

_ROLES = ("Damage Dealer", "Healer", "Tank", "Support DD")
_ALLIANCES = ("", "Aldmeri Dominion", "Daggerfall Covenant", "Ebonheart Pact")

_CREATE_CHARACTER_STYLE = """
QPushButton {
    background-color: #D1983D;
    color: #0C171B;
    border: 1px solid #C8A46A;
    border-radius: 17px;
    padding: 8px 22px;
    font-weight: 700;
}
QPushButton:hover {
    background-color: #DCAA57;
}
QPushButton:pressed {
    background-color: #B97F2F;
}
QPushButton:disabled {
    background-color: #6D5A37;
    color: #BFC8C6;
}
"""

_HERO_STYLE = """
QFrame#newBuildHero {
    border: 1px solid #C8A46A;
    border-radius: 18px;
    background-color: rgba(47, 122, 128, 28);
}
QLabel#newBuildEyebrow {
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#newBuildTitle {
    font-size: 24px;
    font-weight: 700;
}
QFrame#newBuildForm {
    border-top: 1px solid rgba(200, 164, 106, 110);
    border-radius: 0px;
    background: transparent;
}
"""


def _style_create_character_button(button: FoundryButton) -> FoundryButton:
    """Give every creation entry point the same obvious amber pill treatment."""
    button.setStyleSheet(_CREATE_CHARACTER_STYLE)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setMinimumHeight(36)
    button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return button


def _overview_action_pill(text: str) -> FoundryButton:
    """Render the Overview card footer actions as compact secondary pills."""
    button = FoundryButton(text, role=ButtonRole.SECONDARY, compact=True)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return button


class CharacterCreationEasyModePanel(QFrame):
    """Large inline new-build panel owned by the Builds page."""

    def __init__(self, *, page, parent=None) -> None:
        super().__init__(parent)
        self.page = page
        self.reference = page.reference
        self.setObjectName("newBuildHero")
        self.setStyleSheet(_HERO_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(10)

        hero_row = QHBoxLayout()
        hero_row.setSpacing(18)
        copy = QVBoxLayout()
        copy.setSpacing(3)

        eyebrow = QLabel("NEW BUILD • FIELD DESK")
        eyebrow.setObjectName("newBuildEyebrow")
        eyebrow.setProperty("departmentLabel", True)
        copy.addWidget(eyebrow)

        title = QLabel("Build something worth bringing to raid.")
        title.setObjectName("newBuildTitle")
        title.setProperty("pageTitle", True)
        title.setWordWrap(True)
        copy.addWidget(title)

        subtitle = QLabel(
            "Start with the useful basics. FoundryDock creates a clean Default build, "
            "then hands it straight to the full editor below."
        )
        subtitle.setProperty("pageSubtitle", True)
        subtitle.setWordWrap(True)
        copy.addWidget(subtitle)
        hero_row.addLayout(copy, 1)

        self.toggle_button = _style_create_character_button(
            FoundryButton("+ Start a New Build", role=ButtonRole.PRIMARY)
        )
        hero_row.addWidget(self.toggle_button, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(hero_row)

        self.form_panel = QFrame(self)
        self.form_panel.setObjectName("newBuildForm")
        form_root = QVBoxLayout(self.form_panel)
        form_root.setContentsMargins(0, 16, 0, 0)
        form_root.setSpacing(10)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Character name")
        form.addRow("1. Character name *", self.name_edit)

        self.class_combo = QComboBox()
        self.class_combo.addItems([value for value in ESO_CLASSES if str(value).strip()])
        form.addRow("2. Class *", self.class_combo)

        self.race_combo = QComboBox()
        self.race_combo.addItems(list(self.reference.list_race_names()))
        form.addRow("3. Race *", self.race_combo)

        self.role_combo = QComboBox()
        self.role_combo.addItems(_ROLES)
        form.addRow("4. Primary role *", self.role_combo)

        self.gamertag_edit = QLineEdit()
        self.gamertag_edit.setPlaceholderText("Optional")
        form.addRow("5. Account / gamertag", self.gamertag_edit)

        self.alliance_combo = QComboBox()
        self.alliance_combo.addItems(_ALLIANCES)
        form.addRow("6. Alliance", self.alliance_combo)

        set_names = sorted(
            {
                str(name).strip()
                for name in self.reference.list_gear_set_names()
                if str(name).strip()
            },
            key=str.casefold,
        )
        self.body_set_combo = self._searchable_combo(set_names)
        form.addRow("7. Gear on body", self.body_set_combo)

        self.weapon_jewelry_set_combo = self._searchable_combo(set_names)
        form.addRow("8. Gear on weapons / jewelry", self.weapon_jewelry_set_combo)
        form_root.addLayout(form)

        self.advanced_button = FoundryButton(
            "Advanced ▸", role=ButtonRole.SECONDARY, compact=True
        )
        form_root.addWidget(self.advanced_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.advanced_panel = QFrame()
        self.advanced_panel.setProperty("foundryCard", True)
        advanced_layout = QHBoxLayout(self.advanced_panel)
        advanced_layout.setContentsMargins(14, 10, 14, 10)
        advanced_note = QLabel("Optional character state")
        advanced_note.setProperty("sidebarHeading", True)
        advanced_layout.addWidget(advanced_note)
        advanced_layout.addStretch()
        self.vampire_check = QCheckBox("Vampire")
        self.werewolf_check = QCheckBox("Werewolf")
        self.vampire_check.toggled.connect(
            lambda checked: self.werewolf_check.setChecked(False) if checked else None
        )
        self.werewolf_check.toggled.connect(
            lambda checked: self.vampire_check.setChecked(False) if checked else None
        )
        advanced_layout.addWidget(self.vampire_check)
        advanced_layout.addWidget(self.werewolf_check)
        self.advanced_panel.setVisible(False)
        form_root.addWidget(self.advanced_panel)

        actions = QHBoxLayout()
        self.cancel_button = FoundryButton("Never Mind", role=ButtonRole.SECONDARY)
        self.create_button = _style_create_character_button(
            FoundryButton("Create & Open Build", role=ButtonRole.PRIMARY)
        )
        actions.addStretch()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.create_button)
        form_root.addLayout(actions)

        self.form_panel.setVisible(False)
        root.addWidget(self.form_panel)

        self.toggle_button.clicked.connect(self.open_for_creation)
        self.cancel_button.clicked.connect(self.close_form)
        self.create_button.clicked.connect(self.create_build)
        self.advanced_button.clicked.connect(self._toggle_advanced)

    @staticmethod
    def _searchable_combo(values: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItem("")
        combo.addItems(values)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setPlaceholderText("Optional")
        completer = combo.completer()
        if completer is not None:
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
        return combo

    def request(self) -> CharacterCreationRequest:
        return CharacterCreationRequest(
            name=self.name_edit.text(),
            eso_class=self.class_combo.currentText(),
            race=self.race_combo.currentText(),
            role=self.role_combo.currentText(),
            gamertag=self.gamertag_edit.text(),
            alliance=self.alliance_combo.currentText(),
            body_set=self.body_set_combo.currentText(),
            weapons_jewelry_set=self.weapon_jewelry_set_combo.currentText(),
            vampire=self.vampire_check.isChecked(),
            werewolf=self.werewolf_check.isChecked(),
        )

    def open_for_creation(self) -> None:
        self.form_panel.setVisible(True)
        self.toggle_button.setText("NEW BUILD ↓")
        self.name_edit.setFocus()
        scroll = getattr(self.page, "workspace_scroll", None)
        if scroll is not None:
            scroll.verticalScrollBar().setValue(0)

    def close_form(self) -> None:
        self.form_panel.setVisible(False)
        self.toggle_button.setText("+ Start a New Build")

    def _toggle_advanced(self) -> None:
        visible = not self.advanced_panel.isVisible()
        self.advanced_panel.setVisible(visible)
        self.advanced_button.setText("Advanced ▾" if visible else "Advanced ▸")

    def _missing_required_fields(self) -> list[str]:
        missing = []
        if not self.name_edit.text().strip():
            missing.append("Character name")
        if not self.class_combo.currentText().strip():
            missing.append("Class")
        if not self.race_combo.currentText().strip():
            missing.append("Race")
        if not self.role_combo.currentText().strip():
            missing.append("Primary role")
        return missing

    def _reset(self) -> None:
        self.name_edit.clear()
        self.gamertag_edit.clear()
        self.body_set_combo.setCurrentIndex(0)
        self.weapon_jewelry_set_combo.setCurrentIndex(0)
        self.alliance_combo.setCurrentIndex(0)
        self.vampire_check.setChecked(False)
        self.werewolf_check.setChecked(False)
        self.advanced_panel.setVisible(False)
        self.advanced_button.setText("Advanced ▸")

    def create_build(self) -> None:
        missing = self._missing_required_fields()
        if missing:
            self.page.status.warning("New build needs: " + ", ".join(missing) + ".")
            return

        request = self.request()
        duplicate = request.name.strip().casefold()
        if any(
            str(build.Name or "").strip().casefold() == duplicate
            for build in self.page.roster.Members
        ):
            self.page.status.warning(
                f"A character named {request.name.strip()} already exists in Builds."
            )
            return

        service = CharacterCreationService(
            armor_weight_resolver=GearSetArmorWeightResolver(
                self.page.data_dir / "eso.db"
            )
        )
        try:
            build = service.create(request)
        except ValueError as exc:
            self.page.status.error(f"Could not create build: {exc}")
            return

        self.page.roster.Members.append(build)
        self.page.selected_index = len(self.page.roster.Members) - 1
        self.page._save()
        self.page._refresh_roster()
        if self.page.roster_list.count():
            self.page.roster_list.setCurrentRow(self.page.selected_index)

        self.page.status.success(
            f"Created {build.Name} with the {build.BuildName or 'Default'} build."
        )
        self._reset()
        self.close_form()

        tabs = getattr(self.page, "build_tabs", None)
        if tabs is not None and tabs.count() > 1:
            tabs.setCurrentIndex(1)


# Compatibility name for callers/tests that imported the old class. It is no
# longer a dialog and must not be executed with exec().
CharacterCreationEasyModeDialog = CharacterCreationEasyModePanel


def _open_easy_character_creator(page) -> None:
    panel = getattr(page, "new_build_panel", None)
    if panel is not None:
        panel.open_for_creation()


def _open_easy_character_creator_from_overview(console) -> None:
    """Route the Overview CTA through Builds and reveal the inline New Build desk."""
    window = console.window()
    show_page = getattr(window, "show_page", None)
    if callable(show_page):
        show_page("console:2")

    builds_page = getattr(window, "pages", {}).get("console:2")
    if builds_page is None:
        return
    _open_easy_character_creator(builds_page)


def install() -> None:
    """Add the inline Easy Mode front door and tidy the Builds layout."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from ui.operations_console import OperationsConsole
    from widgets.build_editor import BuildEditor

    original_build_ui = BuildsPage._build_ui
    original_role_for = BuildsPage._role_for
    original_raid_status_card = OperationsConsole._raid_status_card
    original_editor_build_ui = BuildEditor._build_ui
    original_identity_card = BuildEditor._build_identity_card

    def _build_ui(self):
        original_build_ui(self)

        action_host = self.edit_button.parentWidget()
        action_layout = action_host.layout() if action_host is not None else None
        if action_layout is not None:
            for index in range(action_layout.count()):
                widget = action_layout.itemAt(index).widget()
                if isinstance(widget, FoundryButton):
                    widget.set_compact(True)

        self.create_character_button = _style_create_character_button(
            FoundryButton("+ New Build", role=ButtonRole.PRIMARY, compact=True)
        )
        self.create_character_button.clicked.connect(
            lambda: _open_easy_character_creator(self)
        )

        if action_layout is not None:
            index = action_layout.indexOf(self.edit_button)
            action_layout.insertWidget(max(index, 0), self.create_character_button)

        self.new_build_panel = CharacterCreationEasyModePanel(
            page=self, parent=self.workspace_widget
        )
        tabs = getattr(self, "build_tabs", None)
        if tabs is not None:
            tab_index = self.workspace_layout.indexOf(tabs)
            self.workspace_layout.insertWidget(max(0, tab_index), self.new_build_panel)
        else:
            self.workspace_layout.insertWidget(0, self.new_build_panel)

    def _role_for(self, build):
        roster_role, status = original_role_for(self, build)
        return roster_role or str(getattr(build, "Role", "") or "").strip(), status

    def _raid_status_card(self):
        host = QWidget()
        host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        create_button = _style_create_character_button(
            FoundryButton("+ New Build", role=ButtonRole.PRIMARY, compact=True)
        )
        create_button.clicked.connect(
            lambda: _open_easy_character_creator_from_overview(self)
        )
        layout.addWidget(create_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(original_raid_status_card(self), 1)
        return host

    def _editor_build_ui(self):
        original_editor_build_ui(self)
        layout = self.layout()
        if layout is not None:
            layout.addStretch(1)

    def _identity_card(self):
        card = original_identity_card(self)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        card.body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return card

    BuildsPage._build_ui = _build_ui
    BuildsPage._role_for = _role_for
    OperationsConsole._raid_status_card = _raid_status_card
    OperationsConsole._compact_button = staticmethod(_overview_action_pill)
    BuildEditor._build_ui = _editor_build_ui
    BuildEditor._build_identity_card = _identity_card
    _INSTALLED = True
