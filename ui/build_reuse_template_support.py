from __future__ import annotations

"""Builds-page UI for exact build copying and reusable role templates."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
)

from engine.config import get_data_dir
from services.build_reuse_service import BuildReuseService, BuildTemplateRecord
from services.user_safety_snapshot_service import UserSafetySnapshotService
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.ui_safety import confirm_replacement


_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_ORIGINAL_REFRESH_ROSTER = None
_ORIGINAL_SELECT_MEMBER = None
_ORIGINAL_REFRESH_DETAIL = None


def _reuse_service() -> BuildReuseService:
    return BuildReuseService(get_data_dir() / "build_templates.json")


def _catalog_snapshot(page):
    catalog = page.build_service.canonical.catalog_service.load()
    players = {
        str(player.get("player_id") or "").strip(): player
        for player in catalog.get("players", [])
        if isinstance(player, dict)
    }
    characters = [row for row in catalog.get("characters", []) if isinstance(row, dict)]
    return players, characters


class _DestinationDialog(QDialog):
    def __init__(self, page, *, title: str, default_build_name: str, include_variants: bool = True):
        super().__init__(page)
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self.players, self.characters = _catalog_snapshot(page)
        self.player_combo = QComboBox()
        self.character_combo = QComboBox()
        self.build_name = QLineEdit(default_build_name)
        self.include_variants = QCheckBox("Include Context Variants")
        self.include_variants.setChecked(include_variants)
        self.include_notes = QCheckBox("Include Notes")
        self.include_notes.setChecked(True)

        player_rows = []
        for player_id, player in self.players.items():
            tag = str(player.get("gamertag") or "").strip()
            label = str(player.get("display_name") or "").strip() or tag
            if tag and tag.casefold() not in label.casefold():
                label = f"{label} • {tag}"
            player_rows.append((label or player_id, player_id))
        for label, player_id in sorted(player_rows, key=lambda row: row[0].casefold()):
            self.player_combo.addItem(label, player_id)

        form = QFormLayout()
        form.addRow("Player", self.player_combo)
        form.addRow("Character", self.character_combo)
        form.addRow("New Build Name", self.build_name)
        form.addRow("", self.include_variants)
        form.addRow("", self.include_notes)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Create Build")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.player_combo.currentIndexChanged.connect(self._refresh_characters)
        self._refresh_characters()

    def _refresh_characters(self):
        player_id = str(self.player_combo.currentData() or "")
        self.character_combo.clear()
        rows = []
        for character in self.characters:
            if str(character.get("player_id") or "").strip() != player_id:
                continue
            name = str(character.get("name") or "").strip()
            eso_class = str(character.get("eso_class") or "").strip()
            label = f"{name} • {eso_class}" if eso_class else name
            rows.append((label or str(character.get("character_id") or ""), character))
        for label, character in sorted(rows, key=lambda row: row[0].casefold()):
            self.character_combo.addItem(label, character)

    @property
    def destination(self):
        character = self.character_combo.currentData()
        if not isinstance(character, dict):
            return None
        player = self.players.get(str(character.get("player_id") or "").strip(), {})
        return {
            "name": str(character.get("name") or "").strip(),
            "gamertag": str(player.get("gamertag") or character.get("gamertag") or "").strip(),
            "eso_class": str(character.get("eso_class") or "").strip(),
            "race": str(character.get("race") or "").strip(),
            "role": str(character.get("role") or "").strip(),
        }


class _TemplateNameDialog(QDialog):
    def __init__(self, page, build):
        super().__init__(page)
        self.setWindowTitle("Save Build as Template")
        self.name = QLineEdit(build.BuildName.strip() or f"{build.Role or 'Build'} Template")
        self.include_variants = QCheckBox("Include Context Variants")
        self.include_variants.setChecked(True)
        self.include_notes = QCheckBox("Include Notes")
        self.include_notes.setChecked(True)
        form = QFormLayout()
        form.addRow("Template Name", self.name)
        form.addRow("Role", QLabel(build.Role or "Unspecified"))
        form.addRow("Class Overlay", QLabel(build.EsoClass or "None"))
        form.addRow("", self.include_variants)
        form.addRow("", self.include_notes)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)


def _build_identity_key(build) -> tuple[str, str, str]:
    return (
        str(getattr(build, "Gamertag", "") or "").strip().casefold(),
        str(getattr(build, "Name", "") or "").strip().casefold(),
        str(getattr(build, "BuildName", "") or "").strip().casefold(),
    )


def _existing_build_for(page, build):
    wanted = _build_identity_key(build)
    return next(
        (
            existing
            for existing in getattr(getattr(page, "roster", None), "Members", ())
            if _build_identity_key(existing) == wanted
        ),
        None,
    )


def _selected_build(page):
    if not page.roster.Members:
        return None
    index = int(getattr(page, "selected_index", -1))
    if index < 0 or index >= len(page.roster.Members):
        return None
    return page.roster.Members[index]


def _copy_selected_build(page):
    source = _selected_build(page)
    if source is None:
        return
    dialog = _DestinationDialog(page, title="Copy Build To…", default_build_name=source.BuildName or "Copied Build")
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    destination = dialog.destination
    if destination is None:
        QMessageBox.warning(page, "Copy Build", "Choose a destination character first.")
        return
    try:
        result = _reuse_service().copy_build(
            source,
            destination_name=destination["name"],
            destination_gamertag=destination["gamertag"],
            destination_class=destination["eso_class"],
            destination_race=destination["race"],
            destination_role=destination["role"],
            new_build_name=dialog.build_name.text().strip(),
            include_variants=dialog.include_variants.isChecked(),
            include_notes=dialog.include_notes.isChecked(),
        )
    except ValueError as exc:
        QMessageBox.warning(page, "Copy Build", str(exc))
        return
    existing = _existing_build_for(page, result.build)
    if existing is not None and not confirm_replacement(
        page,
        title="Replace Existing Build",
        object_label=f'Replace "{existing.BuildName or "build"}" for {existing.Name or existing.Gamertag}?',
        impact=(
            "The existing saved Build with the same player, character, and Build name "
            "will be replaced. Character progression and unrelated Builds are kept."
        ),
        confirm_text="Replace Build",
    ):
        return
    if existing is not None:
        UserSafetySnapshotService().create(
            f"replace-build-{existing.BuildId or existing.BuildName}"
        )
    existing = _existing_build_for(page, result.build)
    if existing is not None and not confirm_replacement(
        page,
        title="Replace Existing Build",
        object_label=f'Replace "{existing.BuildName or "build"}" for {existing.Name or existing.Gamertag}?',
        impact=(
            "Applying this template will replace the saved Build with the same player, "
            "character, and Build name. Other Builds and character progression are kept."
        ),
        confirm_text="Apply and Replace",
    ):
        return
    if existing is not None:
        UserSafetySnapshotService().create(
            f"apply-template-replace-build-{existing.BuildId or existing.BuildName}"
        )
    page.roster = _reuse_service().replace_or_append(page.roster, result.build)
    page.build_service.save(page.roster)
    page._load()
    page.status.success(f"Copied {source.BuildName or 'build'} to {destination['name']}.")


def _save_selected_as_template(page):
    source = _selected_build(page)
    if source is None:
        return
    dialog = _TemplateNameDialog(page, source)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    template_name = dialog.name.text().strip()
    existing_template = next(
        (
            row
            for row in _reuse_service().load_templates()
            if row.template_id == _reuse_service()._stable_id(template_name)
        ),
        None,
    )
    if existing_template is not None and not confirm_replacement(
        page,
        title="Update Build Template",
        object_label=f'Update template "{existing_template.name}"?',
        impact=(
            "The role-level template is kept, but the matching class overlay may be "
            "replaced by the selected Build. Other class overlays remain intact."
        ),
        confirm_text="Update Template",
    ):
        return
    try:
        template = _reuse_service().save_template_from_build(
            source,
            template_name=template_name,
            include_variants=dialog.include_variants.isChecked(),
            include_notes=dialog.include_notes.isChecked(),
        )
    except ValueError as exc:
        QMessageBox.warning(page, "Save Template", str(exc))
        return
    page.status.success(f"Saved template: {template.name}")
    if page.view_combo.currentText() == "Templates":
        page._refresh_roster()


def _apply_template(page, template: BuildTemplateRecord):
    dialog = _DestinationDialog(page, title="Use Template For…", default_build_name=template.name)
    dialog.include_notes.setVisible(False)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    destination = dialog.destination
    if destination is None:
        QMessageBox.warning(page, "Use Template", "Choose a destination character first.")
        return
    result = _reuse_service().apply_template(
        template,
        destination_name=destination["name"],
        destination_gamertag=destination["gamertag"],
        destination_class=destination["eso_class"],
        destination_race=destination["race"],
        destination_role=destination["role"],
        new_build_name=dialog.build_name.text().strip(),
        include_variants=dialog.include_variants.isChecked(),
    )
    existing = _existing_build_for(page, result.build)
    if existing is not None and not confirm_replacement(
        page,
        title="Update Existing Saved Build",
        object_label=f'Update "{existing.BuildName or "build"}" for {existing.Name or existing.Gamertag}?',
        impact=(
            "The existing Saved Build will keep its canonical Player/Character/Build identity "
            "and Raid Plan links. Template-owned build fields will be updated. Character "
            "progression and unrelated Builds are kept."
        ),
        confirm_text="Update Saved Build",
    ):
        return
    if existing is not None:
        UserSafetySnapshotService().create(
            f"apply-template-update-build-{existing.BuildId or existing.BuildName}"
        )

    page.roster = _reuse_service().replace_or_append(page.roster, result.build)
    page.build_service.save(page.roster)

    # Applying a template creates a real canonical Saved Build. Keep both the
    # hidden legacy selector and the visible Phase 14 library in the same mode;
    # otherwise the command-center tab can remain on Templates while the detail
    # pane paints a normal Build underneath the template card.
    page.view_combo.setCurrentText("All Builds")
    tabs = getattr(page, "phase14_library_tabs", None)
    if tabs is not None:
        for index in range(tabs.count()):
            if tabs.tabText(index) == "All":
                tabs.blockSignals(True)
                tabs.setCurrentIndex(index)
                tabs.blockSignals(False)
                break
    page._load()
    if result.warnings:
        QMessageBox.information(page, "Template Applied", "\n".join(result.warnings))
    page.status.success(f"Created saved Build {result.build.BuildName or template.name} for {destination['name']}.")


def _show_template_detail(page, template: BuildTemplateRecord):
    page._clear_detail()
    card = FoundryCard(template.name)
    card.addWidget(QLabel(f"Role: {template.role or 'Unspecified'}"))
    classes = sorted(template.class_overlays)
    card.addWidget(QLabel("Class overlays: " + (", ".join(classes) if classes else "None")))
    hint = QLabel(
        "Role-level gear, CP, attributes, consumables, and Context Variants are reusable. "
        "Class/skill state is applied only when a matching class overlay exists; otherwise those slots stay unresolved for review."
    )
    hint.setWordWrap(True)
    hint.setProperty("muted", True)
    card.addWidget(hint)
    if template.notes:
        note = QLabel(template.notes)
        note.setWordWrap(True)
        card.addWidget(note)
    use = FoundryButton("Create Saved Build…", role=ButtonRole.PRIMARY)
    use.clicked.connect(lambda: _apply_template(page, template))
    card.addWidget(use)
    page.detail_layout.addWidget(card)
    page.detail_layout.addStretch(1)


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI, _ORIGINAL_REFRESH_ROSTER, _ORIGINAL_SELECT_MEMBER, _ORIGINAL_REFRESH_DETAIL
    if _INSTALLED:
        return
    from ui.builds_page import BuildsPage

    _ORIGINAL_BUILD_UI = BuildsPage._build_ui
    _ORIGINAL_REFRESH_ROSTER = BuildsPage._refresh_roster
    _ORIGINAL_SELECT_MEMBER = BuildsPage._select_member
    _ORIGINAL_REFRESH_DETAIL = BuildsPage._refresh_detail

    def build_ui_with_reuse(self):
        _ORIGINAL_BUILD_UI(self)
        if self.view_combo.findText("Templates") < 0:
            self.view_combo.addItem("Templates")
        action_layout = self.edit_button.parentWidget().layout()
        self.copy_build_button = FoundryButton("Copy Build To…", role=ButtonRole.SECONDARY)
        self.template_build_button = FoundryButton("Save as Template", role=ButtonRole.SECONDARY)
        self.copy_build_button.clicked.connect(lambda: _copy_selected_build(self))
        self.template_build_button.clicked.connect(lambda: _save_selected_as_template(self))
        action_layout.insertWidget(1, self.copy_build_button)
        action_layout.insertWidget(2, self.template_build_button)

    def refresh_roster_with_templates(self, *_args):
        if self.view_combo.currentText() != "Templates":
            self._template_rows = ()
            self.edit_button.setEnabled(True)
            self.copy_build_button.setEnabled(True)
            self.template_build_button.setEnabled(True)
            return _ORIGINAL_REFRESH_ROSTER(self, *_args)
        self._template_rows = _reuse_service().load_templates()
        self.edit_button.setEnabled(False)
        self.copy_build_button.setEnabled(False)
        self.template_build_button.setEnabled(False)
        self.roster_list.blockSignals(True)
        self.roster_list.clear()
        for index, template in enumerate(self._template_rows):
            classes = ", ".join(sorted(template.class_overlays)) or "role-only"
            label = f"{template.name}  •  {template.role or 'Unspecified'}  [{classes}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.roster_list.addItem(item)
        if self.roster_list.count():
            self.roster_list.setCurrentRow(0)
        self.roster_list.blockSignals(False)
        self._select_member(self.roster_list.currentRow())

    def select_member_with_templates(self, row: int):
        if self.view_combo.currentText() != "Templates":
            return _ORIGINAL_SELECT_MEMBER(self, row)
        rows = tuple(getattr(self, "_template_rows", ()) or ())
        if row < 0 or row >= len(rows):
            self._clear_detail()
            return
        self._selected_template_index = row
        _show_template_detail(self, rows[row])

    def refresh_detail_with_templates(self, *_args):
        if self.view_combo.currentText() != "Templates":
            return _ORIGINAL_REFRESH_DETAIL(self, *_args)
        rows = tuple(getattr(self, "_template_rows", ()) or ())
        index = int(getattr(self, "_selected_template_index", 0))
        if rows and 0 <= index < len(rows):
            _show_template_detail(self, rows[index])
        else:
            self._clear_detail()

    BuildsPage._build_ui = build_ui_with_reuse
    BuildsPage._refresh_roster = refresh_roster_with_templates
    BuildsPage._select_member = select_member_with_templates
    BuildsPage._refresh_detail = refresh_detail_with_templates
    _INSTALLED = True


__all__ = ["install"]
