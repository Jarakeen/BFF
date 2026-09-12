from __future__ import annotations

"""Simple front-door character creation for the Builds workspace.

This layer deliberately keeps the first-run path small: identity, primary role,
optional starter sets, and optional vampire/werewolf state. The full BuildEditor
remains available after creation for detailed configuration.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
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


class CharacterCreationEasyModeDialog(QDialog):
    """Small, scroll-safe character creation form."""

    def __init__(self, *, reference, parent=None) -> None:
        super().__init__(parent)
        self.reference = reference
        self.setWindowTitle("Build a New Character")
        self.setMinimumSize(620, 560)
        self.resize(720, 760)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        intro = QLabel(
            "Start with the basics. Everything else can be edited after the character is created."
        )
        intro.setWordWrap(True)
        intro.setProperty("pageSubtitle", True)
        root.addWidget(intro)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        host = QWidget()
        content = QVBoxLayout(host)
        content.setContentsMargins(4, 4, 12, 4)
        content.setSpacing(12)

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
            {str(name).strip() for name in self.reference.list_gear_set_names() if str(name).strip()},
            key=str.casefold,
        )
        self.body_set_combo = self._searchable_combo(set_names)
        form.addRow("7. Gear on body", self.body_set_combo)

        self.weapon_jewelry_set_combo = self._searchable_combo(set_names)
        form.addRow("8. Gear on weapons / jewelry", self.weapon_jewelry_set_combo)

        content.addLayout(form)

        self.advanced_button = FoundryButton(
            "Advanced ▸",
            role=ButtonRole.SECONDARY,
            compact=True,
        )
        content.addWidget(self.advanced_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.advanced_panel = QFrame()
        self.advanced_panel.setProperty("foundryCard", True)
        advanced_layout = QVBoxLayout(self.advanced_panel)
        advanced_layout.setContentsMargins(14, 10, 14, 10)
        advanced_note = QLabel("Optional character state")
        advanced_note.setProperty("sidebarHeading", True)
        advanced_layout.addWidget(advanced_note)
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
        content.addWidget(self.advanced_panel)
        content.addStretch(1)

        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = FoundryButton("Cancel", role=ButtonRole.SECONDARY)
        create = FoundryButton("Create Character", role=ButtonRole.SUCCESS)
        cancel.clicked.connect(self.reject)
        create.clicked.connect(self._accept_if_complete)
        actions.addWidget(cancel)
        actions.addWidget(create)
        root.addLayout(actions)

        self.advanced_button.clicked.connect(self._toggle_advanced)
        self.name_edit.setFocus()

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

    def _toggle_advanced(self) -> None:
        visible = not self.advanced_panel.isVisible()
        self.advanced_panel.setVisible(visible)
        self.advanced_button.setText("Advanced ▾" if visible else "Advanced ▸")

    def _accept_if_complete(self) -> None:
        missing = []
        if not self.name_edit.text().strip():
            missing.append("Character name")
        if not self.class_combo.currentText().strip():
            missing.append("Class")
        if not self.race_combo.currentText().strip():
            missing.append("Race")
        if not self.role_combo.currentText().strip():
            missing.append("Primary role")
        if missing:
            QMessageBox.warning(
                self,
                "Character needs a few basics",
                "Please fill in: " + ", ".join(missing),
            )
            return
        self.accept()

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


def _open_easy_character_creator(page) -> None:
    dialog = CharacterCreationEasyModeDialog(reference=page.reference, parent=page)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    request = dialog.request()
    duplicate = request.name.strip().casefold()
    if any(str(build.Name or "").strip().casefold() == duplicate for build in page.roster.Members):
        QMessageBox.warning(
            page,
            "Character already exists",
            f"A character named {request.name.strip()} already exists in Builds.",
        )
        return

    service = CharacterCreationService(
        armor_weight_resolver=GearSetArmorWeightResolver(page.data_dir / "eso.db")
    )
    try:
        build = service.create(request)
    except ValueError as exc:
        QMessageBox.warning(page, "Could not create character", str(exc))
        return

    page.roster.Members.append(build)
    page.selected_index = len(page.roster.Members) - 1
    page._save()
    page._refresh_roster()
    if page.roster_list.count():
        page.roster_list.setCurrentRow(page.selected_index)
    page.status.success(
        f"Created {build.Name} with the {build.BuildName or 'Default'} build."
    )


def install() -> None:
    """Add the visible Easy Mode character-creation front door to Builds."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    original_build_ui = BuildsPage._build_ui
    original_role_for = BuildsPage._role_for

    def _build_ui(self):
        original_build_ui(self)
        self.create_character_button = FoundryButton(
            "+ Create Character",
            role=ButtonRole.PRIMARY,
        )
        self.create_character_button.clicked.connect(
            lambda: _open_easy_character_creator(self)
        )

        action_host = self.edit_button.parentWidget()
        action_layout = action_host.layout() if action_host is not None else None
        if action_layout is not None:
            index = action_layout.indexOf(self.edit_button)
            action_layout.insertWidget(max(index, 0), self.create_character_button)

    def _role_for(self, build):
        roster_role, status = original_role_for(self, build)
        return roster_role or str(getattr(build, "Role", "") or "").strip(), status

    BuildsPage._build_ui = _build_ui
    BuildsPage._role_for = _role_for
    _INSTALLED = True
