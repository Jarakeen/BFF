from __future__ import annotations

"""Phase 14 build-profile UI over the command-center shell.

This layer makes Favorites/Archive/ownership filters real and surfaces the editable
build-level gear baseline. It persists only additive profile metadata in
``build_profiles.json``; it never rewrites the saved build or canonical ESO database.
"""

from copy import deepcopy

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from engine.config import get_data_dir
from models.build_model import ARMOR_TRAITS, JEWELRY_TRAITS
from widgets.build_editor import ENCHANT_CHOICES
from services.build_profile_service import (
    BuildProfile,
    BuildProfileService,
    build_profile_exception_count,
)
from services.build_rotation_artifact_service import resolve_canonical_build_id
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard

_INSTALLED = False
_ORIGINAL_REFRESH_DETAIL = None


def _service() -> BuildProfileService:
    return BuildProfileService(get_data_dir() / "build_profiles.json")


def _selected_build(page):
    index = int(getattr(page, "selected_index", -1))
    if index < 0 or index >= len(page.roster.Members):
        return None
    return page.roster.Members[index]


def _build_id(page, build) -> str:
    if build is None:
        return ""
    try:
        return str(
            resolve_canonical_build_id(page.build_service.canonical.catalog_service, build)
            or ""
        ).strip()
    except Exception:
        return ""


def _profile(page, build) -> BuildProfile:
    build_id = _build_id(page, build)
    return _service().get(build_id) if build_id else BuildProfile()


def _profile_matches_mode(page, build) -> bool:
    mode = str(page.phase14_library_tabs.tabText(page.phase14_library_tabs.currentIndex()) or "All")
    profile = _profile(page, build)
    if mode == "Archive":
        return profile.archived
    if profile.archived:
        return False
    if mode == "Mine":
        return profile.ownership == "mine"
    if mode == "Team":
        return profile.ownership == "team"
    if mode == "Comp Builds":
        return str(getattr(build, "BuildKind", "saved") or "saved").strip().casefold() == "comp"
    if mode == "Favorites":
        return profile.favorite
    return mode == "All"


def _populate_profile_table(page) -> None:
    from ui import phase14_builds_command_center_support as command_center

    table = page.phase14_build_table
    table.blockSignals(True)
    table.setRowCount(0)
    page.phase14_table_source_rows = []

    if command_center._template_mode(page):
        for source_row in range(page.roster_list.count()):
            item = page.roster_list.item(source_row)
            row = table.rowCount()
            table.insertRow(row)
            for column, value in enumerate(("☆", item.text(), "Template", "—", "Template", "Reusable")):
                from PySide6.QtWidgets import QTableWidgetItem
                table.setItem(row, column, QTableWidgetItem(value))
            page.phase14_table_source_rows.append(source_row)
        table.blockSignals(False)
        if table.rowCount():
            table.selectRow(0)
        return

    from PySide6.QtWidgets import QTableWidgetItem
    for build_index, build in enumerate(page.roster.Members):
        if not _profile_matches_mode(page, build):
            continue
        if not command_center._build_matches_filters(page, build):
            continue
        profile = _profile(page, build)
        character = str(getattr(build, "Name", "") or "").strip() or "Unnamed Character"
        build_name = str(getattr(build, "BuildName", "") or "").strip() or "Default"
        values = (
            "★" if profile.favorite else "☆",
            f"{character} — {build_name}",
            character,
            str(getattr(build, "EsoClass", "") or "").strip() or "—",
            command_center._role_for_row(page, build) or "—",
            command_center._content_for_build(build),
        )
        row = table.rowCount()
        table.insertRow(row)
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(value))
        page.phase14_table_source_rows.append(build_index)

    table.blockSignals(False)
    if table.rowCount():
        desired = 0
        if page.selected_index in page.phase14_table_source_rows:
            desired = page.phase14_table_source_rows.index(page.selected_index)
        table.selectRow(desired)


def _toggle_favorite(page, row: int, column: int) -> None:
    if column != 0 or row < 0 or row >= len(getattr(page, "phase14_table_source_rows", ())):
        return
    from ui import phase14_builds_command_center_support as command_center
    if command_center._template_mode(page):
        return
    index = page.phase14_table_source_rows[row]
    if index < 0 or index >= len(page.roster.Members):
        return
    build = page.roster.Members[index]
    build_id = _build_id(page, build)
    if not build_id:
        page.status.warning("This saved build has no canonical build id yet; favorite state was not changed.")
        return
    profile = _service().get(build_id)
    _service().update(build_id, favorite=not profile.favorite)
    _populate_profile_table(page)
    page._refresh_detail()


class _BaselineDialog(QDialog):
    def __init__(self, page, profile: BuildProfile):
        super().__init__(page)
        self.setWindowTitle("Build Baseline")
        self.setMinimumWidth(430)
        self.quality = QComboBox()
        self.quality.addItems(["Gold", "Purple", "Blue", "Green", "White"])
        self.level = QComboBox()
        self.level.setEditable(True)
        self.level.addItems(["CP160", "CP150", "Level 50"])
        self.tier = QComboBox()
        self.tier.setEditable(True)
        self.tier.addItems(["Truly Superb", "Superb", "Greater", "Major", "Minor"])
        self.armor_trait = QComboBox()
        self.armor_trait.addItems(["", *[value for value in ARMOR_TRAITS if value]])
        self.armor_weight = QComboBox()
        self.armor_weight.addItems(["", "Light", "Medium", "Heavy"])
        self.armor_enchant = QComboBox()
        self.armor_enchant.setEditable(True)
        self.armor_enchant.addItems(["", *[value for value in ENCHANT_CHOICES if value in {"Max Magicka", "Max Health", "Max Stamina", "Prismatic Defense"}]])
        self.jewelry_trait = QComboBox()
        self.jewelry_trait.addItems(["", *[value for value in JEWELRY_TRAITS if value]])
        self.jewelry_enchant = QComboBox()
        self.jewelry_enchant.setEditable(True)
        self.jewelry_enchant.addItems(["", *[value for value in ENCHANT_CHOICES if value in {"Magicka Recovery", "Health Recovery", "Stamina Recovery", "Weapon Damage", "Spell Damage", "Decrease Physical Harm"}]])

        self.quality.setCurrentText(profile.quality)
        self.level.setCurrentText(profile.item_level)
        self.tier.setCurrentText(profile.enchantment_tier)
        self.armor_trait.setCurrentText(profile.armor_trait)
        self.armor_weight.setCurrentText(profile.armor_weight)
        self.armor_enchant.setCurrentText(profile.armor_enchant)
        self.jewelry_trait.setCurrentText(profile.jewelry_trait)
        self.jewelry_enchant.setCurrentText(profile.jewelry_enchant)

        form = QFormLayout()
        form.addRow("Quality", self.quality)
        form.addRow("Item level", self.level)
        form.addRow("Enchantment tier", self.tier)
        form.addRow("Armor trait", self.armor_trait)
        form.addRow("Armor weight", self.armor_weight)
        form.addRow("Armor enchant", self.armor_enchant)
        form.addRow("Jewelry trait", self.jewelry_trait)
        form.addRow("Jewelry enchant", self.jewelry_enchant)
        hint = QLabel(
            "Blank equipped-item fields inherit these values. Leave a trait, weight, or enchant blank for per-slot choices. Existing explicit item values are always preserved."
        )
        hint.setWordWrap(True)
        hint.setProperty("muted", True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)


def _fill_blank_profile_fields(build, profile: BuildProfile) -> int:
    """Materialize selected baseline defaults into blank equipped gear fields."""
    changed = 0
    normalized = profile.normalized()

    for item in build.Armor.values():
        equipped = any(str(item.get(key) or "").strip() for key in ("Set", "Set2"))
        if not equipped:
            continue
        for key, value in (
            ("Quality", normalized.quality),
            ("Level", normalized.item_level),
            ("EnchantTier", normalized.enchantment_tier),
            ("Trait", normalized.armor_trait),
            ("Weight", normalized.armor_weight),
            ("Enchant", normalized.armor_enchant),
        ):
            if value and not str(item.get(key) or "").strip():
                item[key] = value
                changed += 1

    for name in ("Necklace", "Ring1", "Ring2"):
        item = getattr(build, name)
        if item.is_empty:
            continue
        for field, value in (
            ("Quality", normalized.quality),
            ("Level", normalized.item_level),
            ("EnchantTier", normalized.enchantment_tier),
            ("Trait", normalized.jewelry_trait),
            ("Enchant", normalized.jewelry_enchant),
        ):
            if value and not str(getattr(item, field, "") or "").strip():
                setattr(item, field, value)
                changed += 1

    for name in ("FrontBarWeapon", "FrontBarOffHand", "BackBarWeapon", "BackBarOffHand"):
        item = getattr(build, name)
        if item.is_empty:
            continue
        for field, value in (
            ("Quality", normalized.quality),
            ("Level", normalized.item_level),
            ("EnchantTier", normalized.enchantment_tier),
        ):
            if value and not str(getattr(item, field, "") or "").strip():
                setattr(item, field, value)
                changed += 1
    return changed


def _edit_baseline(page, build) -> None:
    build_id = _build_id(page, build)
    if not build_id:
        page.status.warning("This saved build has no canonical build id yet; baseline was not changed.")
        return
    service = _service()
    dialog = _BaselineDialog(page, service.get(build_id))
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    try:
        profile = service.update(
            build_id,
            quality=dialog.quality.currentText().strip(),
            item_level=dialog.level.currentText().strip(),
            enchantment_tier=dialog.tier.currentText().strip(),
            armor_trait=dialog.armor_trait.currentText().strip(),
            armor_weight=dialog.armor_weight.currentText().strip(),
            armor_enchant=dialog.armor_enchant.currentText().strip(),
            jewelry_trait=dialog.jewelry_trait.currentText().strip(),
            jewelry_enchant=dialog.jewelry_enchant.currentText().strip(),
        )
    except ValueError as exc:
        page.status.error(f"Build baseline rejected: {exc}")
        return

    original = deepcopy(build)
    filled = _fill_blank_profile_fields(build, profile)
    if filled:
        page._save()
        # _save reports verification failures without raising. Confirm the selected
        # canonical Build survived before claiming the materialization succeeded.
        persisted = next(
            (
                candidate for candidate in page.roster.Members
                if str(getattr(candidate, "BuildId", "") or "").strip() == build_id
            ),
            None,
        )
        if persisted is None:
            index = int(getattr(page, "selected_index", -1))
            if 0 <= index < len(page.roster.Members):
                page.roster.Members[index] = original
            page.status.error("Baseline defaults could not be verified in the Saved Build.")
            return

    page._refresh_detail()
    if filled:
        page.status.success(
            f"Build baseline updated and filled {filled} blank equipped gear field"
            + ("" if filled == 1 else "s")
            + ". Existing values were preserved."
        )
    else:
        page.status.success("Build baseline updated. No equipped blank fields needed filling.")


class _OwnershipDialog(QDialog):
    def __init__(self, page, profile: BuildProfile):
        super().__init__(page)
        self.setWindowTitle("Build Ownership")
        self.setMinimumWidth(430)

        self.ownership = QComboBox()
        self.ownership.addItem("My Build", "mine")
        self.ownership.addItem("Team / Other Player", "team")
        wanted = self.ownership.findData(profile.ownership)
        self.ownership.setCurrentIndex(wanted if wanted >= 0 else 0)

        self.source_owner = QLineEdit()
        self.source_owner.setPlaceholderText("Player / source name")
        self.source_owner.setText(profile.source_owner)

        form = QFormLayout()
        form.addRow("Ownership", self.ownership)
        form.addRow("Owner / source", self.source_owner)

        hint = QLabel(
            "Ownership is library metadata keyed to the canonical BuildId. "
            "It changes Mine/Team filtering only; it does not copy or rewrite the saved build."
        )
        hint.setWordWrap(True)
        hint.setProperty("muted", True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

        self.ownership.currentIndexChanged.connect(self._sync_owner_field)
        self._sync_owner_field()

    def _sync_owner_field(self) -> None:
        team_owned = self.ownership.currentData() == "team"
        self.source_owner.setEnabled(team_owned)
        if not team_owned:
            self.source_owner.clear()


def _edit_ownership(page, build) -> None:
    build_id = _build_id(page, build)
    if not build_id:
        page.status.warning(
            "This saved build has no canonical build id yet; ownership was not changed."
        )
        return

    service = _service()
    dialog = _OwnershipDialog(page, service.get(build_id))
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    ownership = str(dialog.ownership.currentData() or "mine").strip()
    source_owner = dialog.source_owner.text().strip() if ownership == "team" else ""
    service.update(
        build_id,
        ownership=ownership,
        source_owner=source_owner,
    )

    from ui import phase14_builds_command_center_support as command_center

    current_mode = command_center._active_library_mode(page)
    if current_mode in {"Mine", "Team"}:
        command_center._select_library_mode(
            page,
            "Team" if ownership == "team" else "Mine",
        )
    _populate_profile_table(page)
    page._refresh_detail()
    label = source_owner or "Team / Other Player"
    page.status.success(
        f"Build ownership updated: {label if ownership == 'team' else 'My Build'}."
    )


def _toggle_archive(page, build) -> None:
    build_id = _build_id(page, build)
    if not build_id:
        return
    profile = _service().get(build_id)
    action = "restore" if profile.archived else "archive"
    if not profile.archived:
        result = QMessageBox.question(
            page,
            "Archive Build",
            "Archive this build? It remains saved and can be restored from the Archive tab.",
        )
        if result != QMessageBox.StandardButton.Yes:
            return
    _service().update(build_id, archived=not profile.archived)
    _populate_profile_table(page)
    page.status.success(f"Build {action}d.")


def _baseline_card(page, build) -> FoundryCard:
    profile = _profile(page, build)
    exceptions = build_profile_exception_count(build, profile)
    title = "Endgame baseline" if (
        profile.quality == "Gold"
        and profile.item_level == "CP160"
        and profile.enchantment_tier == "Truly Superb"
    ) else "Build baseline"
    card = FoundryCard(title, "◆")
    row = QHBoxLayout()
    summary = QLabel(f"{profile.quality}  •  {profile.item_level}  •  {profile.enchantment_tier}")
    defaults = [
        value for value in (
            profile.armor_trait, profile.armor_weight, profile.armor_enchant,
            profile.jewelry_trait, profile.jewelry_enchant,
        ) if value
    ]
    if defaults:
        summary.setToolTip("Additional defaults: " + " • ".join(defaults))
    summary.setProperty("cardBadge", True)
    row.addWidget(summary)
    row.addStretch(1)
    ownership = "My Build" if profile.ownership == "mine" else (profile.source_owner or "Team Build")
    owner = QLabel(ownership)
    owner.setProperty("cardBadge", True)
    row.addWidget(owner)
    exception = QLabel(f"{exceptions} exception" + ("" if exceptions == 1 else "s"))
    exception.setProperty("cardBadge", True)
    row.addWidget(exception)
    ownership_edit = FoundryButton("Ownership", role=ButtonRole.SECONDARY, compact=True)
    ownership_edit.clicked.connect(lambda: _edit_ownership(page, build))
    row.addWidget(ownership_edit)
    edit = FoundryButton("Edit Baseline", role=ButtonRole.SECONDARY, compact=True)
    edit.clicked.connect(lambda: _edit_baseline(page, build))
    row.addWidget(edit)
    archive = FoundryButton("Restore" if profile.archived else "Archive", role=ButtonRole.SECONDARY, compact=True)
    archive.clicked.connect(lambda: _toggle_archive(page, build))
    row.addWidget(archive)
    card.addLayout(row)
    return card


def install() -> None:
    global _INSTALLED, _ORIGINAL_REFRESH_DETAIL
    if _INSTALLED:
        return
    from ui import phase14_builds_command_center_support as command_center
    from ui.builds_page import BuildsPage

    command_center._populate_build_table = _populate_profile_table
    _ORIGINAL_REFRESH_DETAIL = BuildsPage._refresh_detail

    def refresh_detail_with_profile(self, *_args):
        result = _ORIGINAL_REFRESH_DETAIL(self, *_args)
        from ui import phase14_builds_command_center_support as cc
        if cc._template_mode(self):
            return result
        build = _selected_build(self)
        if build is not None and self.detail_layout.count():
            self.detail_layout.insertWidget(1, _baseline_card(self, build))
        return result

    BuildsPage._refresh_detail = refresh_detail_with_profile
    # The command-center selection handler still selects the build; this second
    # handler gives the star column its own additive metadata action.
    original_create = command_center._create_command_center

    def create_with_profile(page):
        host = original_create(page)
        page.phase14_build_table.cellClicked.connect(lambda row, col: _toggle_favorite(page, row, col))
        return host

    command_center._create_command_center = create_with_profile
    _INSTALLED = True


__all__ = ["install"]
