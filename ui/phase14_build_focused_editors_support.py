from __future__ import annotations

"""Phase 14 focused Build editors and dossier-style inspector.

The Phase 14 Builds library is the primary workspace. Editing one section opens a
small modal that owns only that section instead of constructing the monolithic legacy
BuildEditor. Superseded editor surfaces are not exposed in the Phase 14 workspace.
"""

from collections import Counter
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from models.build_model import (
    ARMOR_SLOTS,
    ARMOR_TRAITS,
    JEWELRY_TRAITS,
    WEAPON_TRAITS,
    GearSlot,
)
from models.roster_model import ESO_CLASSES
from services.skill_choice_service import load_skill_choices
from ui.components.eligible_build_editor import EligibleSkillBarRow
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.ux_icons import icon as semantic_icon, icon_label
from widgets.build_editor import ChampionPointGrid, GearSlotRow

_INSTALLED = False

_SLOT_ICONS = {
    "Head": "viking-helmet",
    "Shoulders": "spiked-shoulder-armor",
    "Chest": "leather-armor",
    "Hands": "mailed-fist",
    "Waist": "metal-skirt",
    "Legs": "greaves",
    "Feet": "metal-boot",
    "Neck": "heart-necklace",
    "Ring 1": "ring",
    "Ring 2": "ring",
    "Main Hand": "lunar-wand",
    "Off Hand": "shield",
}

_ROLE_ICONS = {
    "healer": ("health", "#59AEB3"),
    "tank": ("shield", "#8FA8B8"),
    "damage dealer": ("set", "#C8A46A"),
    "dd": ("set", "#C8A46A"),
    "support dd": ("set", "#C8A46A"),
}


# Reviewed user-supplied trait icon vocabulary. The icon resolver tolerates
# hyphen/underscore filename variants, while these aliases preserve the ESO term
# shown in the UI. A couple of intentionally shared glyphs (Nirnhoned and
# Bloodthirsty -> drop) follow the supplied visual vocabulary exactly.
_TRAIT_ICONS = {
    "Powered": "Powered",
    "Charged": "Charged",
    "Precise": "Precise",
    "Infused": "Infused",
    "Defending": "Defending",
    "Training": "Training",
    "Sharpened": "Sharpened",
    "Decisive": "Decisive",
    "Nirnhoned": "drop",
    "Sturdy": "Sturdy",
    "Impenetrable": "Impenetrable",
    "Reinforced": "Reinforced",
    "Well-Fitted": "Well-fitted",
    "Invigorating": "Invigorating",
    "Divines": "Divines",
    "Healthy": "Health",
    "Arcane": "magic",
    "Robust": "Robust",
    "Bloodthirsty": "drop",
    "Harmony": "Harmony",
    "Triune": "Triune",
    "Protective": "Protective",
    "Swift": "Swift",
}


def _trait_icon_name(value: str) -> str:
    text = str(value or "").strip()
    return _TRAIT_ICONS.get(text, _TRAIT_ICONS.get(text.title(), ""))


def _decorate_trait_combo(combo: QComboBox) -> None:
    """Attach the reviewed trait glyphs without changing combo values."""
    for index in range(combo.count()):
        text = str(combo.itemText(index) or "").strip()
        icon_name = _trait_icon_name(text)
        if not icon_name:
            continue
        value = semantic_icon(icon_name)
        if not value.isNull():
            combo.setItemIcon(index, value)
    combo.setIconSize(QSize(18, 18))


def _selected_build(page):
    index = int(getattr(page, "selected_index", -1))
    if index < 0 or index >= len(page.roster.Members):
        return None
    return page.roster.Members[index]


def _text(value, fallback: str = "—") -> str:
    value = str(value or "").strip()
    return value or fallback


def _editable_combo(values) -> QComboBox:
    combo = QComboBox()
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.addItem("")
    combo.addItems([str(value) for value in values if str(value or "").strip()])
    completer = combo.completer()
    if completer is not None:
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
    return combo


def _persist(page, message: str) -> None:
    page._save()
    page._refresh_roster()
    page._refresh_detail()
    status = getattr(page, "status", None)
    if status is not None:
        status.success(message)


class _FocusedDialog(QDialog):
    def __init__(self, page, title: str, *, width: int = 980, height: int = 620):
        super().__init__(page)
        self.page = page
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(width, height)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(14, 14, 14, 14)
        self.root.setSpacing(10)

    def add_actions(self, save_text: str = "Save") -> None:
        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = FoundryButton("Cancel", role=ButtonRole.SECONDARY, compact=True)
        save = FoundryButton(save_text, role=ButtonRole.PRIMARY, compact=True)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(save)
        self.root.addLayout(actions)


def _gear_slot(value) -> GearSlot:
    if isinstance(value, GearSlot):
        return value
    if isinstance(value, dict):
        return GearSlot.from_dict(value)
    return GearSlot()


def _gear_row_grid(grid: QGridLayout, row_index: int, slot_name: str, controller: GearSlotRow, *, kind: str) -> None:
    icon = icon_label(_SLOT_ICONS.get(slot_name, "leather-armor"), 22)
    grid.addWidget(icon, row_index, 0)
    grid.addWidget(QLabel(slot_name), row_index, 1)
    grid.addWidget(controller.set_combo, row_index, 2)
    grid.addWidget(controller.quality_combo, row_index, 3)
    grid.addWidget(controller.trait_combo, row_index, 4)
    if kind in {"armor", "weapon"}:
        grid.addWidget(controller.type_combo, row_index, 5)
        enchant_column = 6
    else:
        enchant_column = 5
    grid.addWidget(controller.enchant_combo, row_index, enchant_column)
    grid.addWidget(controller.enchant_tier_combo, row_index, enchant_column + 1)
    grid.addWidget(controller.enchant_quality_combo, row_index, enchant_column + 2)
    grid.addWidget(controller.level_combo, row_index, enchant_column + 3)


class _GearDialog(_FocusedDialog):
    def __init__(self, page, build, section: str):
        super().__init__(page, f"{section} — {build.Name} / {build.BuildName}", width=1240, height=640)
        self.build = build
        self.section = section
        self.rows: list[tuple[str, GearSlotRow]] = []
        set_choices = page.reference.list_gear_set_names()

        planned_sets = [
            str(value).strip()
            for value in (getattr(build, "PlannedGearSets", ()) or ())
            if str(value).strip()
        ]
        if planned_sets:
            plan_card = FoundryCard("Comp Plan", "clipboard")
            note = QLabel(
                "Planned in Comp Maker. These sets are not assigned to exact gear slots yet."
            )
            note.setWordWrap(True)
            note.setProperty("muted", True)
            plan_card.addWidget(note)
            planned = QLabel(" + ".join(planned_sets))
            planned.setWordWrap(True)
            plan_card.addWidget(planned)
            self.root.addWidget(plan_card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        headers = ["", "Slot", "Set", "Quality", "Trait"]
        if section in {"Armor", "Front Bar", "Back Bar"}:
            headers.append("Weight / Weapon")
        headers.extend(["Enchantment", "Enchant Tier", "Glyph Quality", "Level"])
        for column, label in enumerate(headers):
            heading = QLabel(label)
            heading.setProperty("sidebarHeading", True)
            heading.setMinimumHeight(24)
            heading.setMaximumHeight(28)
            heading.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(heading, 0, column)

        if section == "Armor":
            source = [(slot, build.Armor.get(slot, {})) for slot in ARMOR_SLOTS]
            kind = "armor"
            trait_choices = ARMOR_TRAITS
        elif section == "Jewelry":
            source = [("Neck", build.Necklace), ("Ring 1", build.Ring1), ("Ring 2", build.Ring2)]
            kind = "jewelry"
            trait_choices = JEWELRY_TRAITS
        elif section == "Front Bar":
            source = [("Main Hand", build.FrontBarWeapon), ("Off Hand", build.FrontBarOffHand)]
            kind = "weapon"
            trait_choices = WEAPON_TRAITS
        else:
            source = [("Main Hand", build.BackBarWeapon), ("Off Hand", build.BackBarOffHand)]
            kind = "weapon"
            trait_choices = WEAPON_TRAITS

        for row_index, (slot_name, value) in enumerate(source, start=1):
            controller = GearSlotRow(
                set_choices,
                trait_choices,
                armor=kind == "armor",
                weapon=kind == "weapon",
                parent=body,
            )
            controller.hide()
            controller.load(_gear_slot(value))
            _decorate_trait_combo(controller.trait_combo)
            self.rows.append((slot_name, controller))
            _gear_row_grid(grid, row_index, slot_name, controller, kind=kind)

        # The scroll viewport is intentionally taller than short sections like
        # Jewelry. Without an explicit stretch row, QGridLayout can donate that
        # spare height to the header row and create a huge blank band above the
        # controls. Keep all editor rows packed at the top and put spare height
        # below the last real row instead.
        grid.setRowStretch(0, 0)
        for row_index in range(1, len(source) + 1):
            grid.setRowStretch(row_index, 0)
        grid.setRowStretch(len(source) + 1, 1)

        grid.setColumnStretch(2, 2)
        for column in range(3, grid.columnCount()):
            grid.setColumnStretch(column, 1)
        scroll.setWidget(body)
        self.root.addWidget(scroll, 1)
        self.add_actions(f"Save {section}")

    def apply(self) -> None:
        values = {slot: row.value for slot, row in self.rows}
        if self.section == "Armor":
            for slot, value in values.items():
                self.build.Armor[slot] = value.to_dict()
        elif self.section == "Jewelry":
            self.build.Necklace = values["Neck"]
            self.build.Ring1 = values["Ring 1"]
            self.build.Ring2 = values["Ring 2"]
        elif self.section == "Front Bar":
            self.build.FrontBarWeapon = values["Main Hand"]
            self.build.FrontBarOffHand = values["Off Hand"]
        else:
            self.build.BackBarWeapon = values["Main Hand"]
            self.build.BackBarOffHand = values["Off Hand"]


class _SkillsDialog(_FocusedDialog):
    def __init__(self, page, build):
        super().__init__(page, f"Skills — {build.Name} / {build.BuildName}", width=1180, height=410)
        self.build = build
        choices = load_skill_choices(page.data_dir / "eso.db")
        self.front = EligibleSkillBarRow(choices)
        self.back = EligibleSkillBarRow(choices)
        for bar in (self.front, self.back):
            bar.set_class(build.EsoClass)
        self.front.load(build.FrontBarSkills)
        self.back.load(build.BackBarSkills)

        planned_skills = [
            str(value).strip()
            for value in (getattr(build, "PlannedSkills", ()) or ())
            if str(value).strip()
        ]
        if planned_skills:
            plan_card = FoundryCard("Comp Plan", "clipboard")
            note = QLabel(
                "Planned in Comp Maker. These skills are not assigned to exact bar slots yet."
            )
            note.setWordWrap(True)
            note.setProperty("muted", True)
            plan_card.addWidget(note)
            planned = QLabel(", ".join(planned_skills))
            planned.setWordWrap(True)
            plan_card.addWidget(planned)
            self.root.addWidget(plan_card)

        card = FoundryCard("Skill Bars", "book-open-text")
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(14)
        form.addRow("Front Bar", self.front)
        form.addRow("Back Bar", self.back)
        card.addLayout(form)
        self.root.addWidget(card, 1)
        self.add_actions("Save Skills")

    def apply(self) -> None:
        self.build.FrontBarSkills = list(self.front.value)
        self.build.BackBarSkills = list(self.back.value)


class _ConsumablesDialog(_FocusedDialog):
    def __init__(self, page, build):
        super().__init__(page, f"Consumables — {build.Name} / {build.BuildName}", width=620, height=260)
        self.build = build
        self.food = _editable_combo(page.reference.list_food_names())
        self.potion = _editable_combo(page.reference.list_potion_names())
        self.food.setCurrentText(build.Food)
        self.potion.setCurrentText(build.Potion)
        form = QFormLayout()
        form.addRow("Food", self.food)
        form.addRow("Potion", self.potion)
        self.root.addLayout(form)
        self.add_actions("Save Consumables")

    def apply(self) -> None:
        self.build.Food = self.food.currentText().strip()
        self.build.Potion = self.potion.currentText().strip()


class _CPDialog(_FocusedDialog):
    def __init__(self, page, build):
        super().__init__(page, f"Champion Points — {build.Name} / {build.BuildName}", width=1180, height=390)
        self.build = build
        choices = [row for row in page.reference.list_champion_points() if isinstance(row, dict)]
        self.grid = ChampionPointGrid(choices)
        self.grid.load_entries(build.ChampionPoints)
        self.root.addWidget(self.grid, 1)
        self.add_actions("Save CP")

    def apply(self) -> None:
        self.build.ChampionPoints = list(self.grid.value)


class _NotesDialog(_FocusedDialog):
    def __init__(self, page, build):
        super().__init__(page, f"Notes — {build.Name} / {build.BuildName}", width=720, height=430)
        self.build = build
        self.notes = QTextEdit()
        self.notes.setPlainText(build.Notes)
        self.root.addWidget(self.notes, 1)
        self.add_actions("Save Notes")

    def apply(self) -> None:
        self.build.Notes = self.notes.toPlainText().strip()


class _IdentityDialog(_FocusedDialog):
    def __init__(self, page, build):
        super().__init__(page, f"Build Identity — {build.Name} / {build.BuildName}", width=620, height=440)
        self.build = build
        self.build_name = QLineEdit(build.BuildName)
        self.character = QLineEdit(build.Name)
        self.race = _editable_combo(page.reference.list_race_names())
        self.eso_class = _editable_combo(ESO_CLASSES)
        self.role = _editable_combo(("Damage Dealer", "Healer", "Tank", "Support DD"))
        self.alliance = _editable_combo(("", "Aldmeri Dominion", "Daggerfall Covenant", "Ebonheart Pact"))
        self.mundus = _editable_combo((
            "The Apprentice", "The Atronach", "The Lady", "The Lord", "The Lover", "The Mage",
            "The Ritual", "The Serpent", "The Shadow", "The Steed", "The Thief", "The Tower", "The Warrior",
        ))
        for combo, value in (
            (self.race, build.Race), (self.eso_class, build.EsoClass), (self.role, build.Role),
            (self.alliance, build.Alliance), (self.mundus, build.Mundus),
        ):
            combo.setCurrentText(value)

        form = QFormLayout()
        form.addRow("Build name", self.build_name)
        form.addRow("Character", self.character)
        form.addRow("Race", self.race)
        form.addRow("Class", self.eso_class)
        form.addRow("Role", self.role)
        form.addRow("Alliance", self.alliance)
        form.addRow("Mundus", self.mundus)
        self.root.addLayout(form)
        self.add_actions("Save Identity")

    def apply(self) -> None:
        self.build.BuildName = self.build_name.text().strip()
        self.build.Name = self.character.text().strip()
        self.build.Race = self.race.currentText().strip()
        self.build.EsoClass = self.eso_class.currentText().strip()
        self.build.Role = self.role.currentText().strip()
        self.build.Alliance = self.alliance.currentText().strip()
        self.build.Mundus = self.mundus.currentText().strip()


def _run_dialog(page, dialog, message: str) -> None:
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    dialog.apply()
    _persist(page, message)


def _edit_gear(page, section: str) -> None:
    build = _selected_build(page)
    if build is None:
        return
    _run_dialog(page, _GearDialog(page, build, section), f"{section} updated.")


def _edit_skills(page) -> None:
    build = _selected_build(page)
    if build is None:
        return
    _run_dialog(page, _SkillsDialog(page, build), "Skill bars updated.")


def _edit_consumables(page) -> None:
    build = _selected_build(page)
    if build is None:
        return
    _run_dialog(page, _ConsumablesDialog(page, build), "Consumables updated.")


def _edit_cp(page) -> None:
    build = _selected_build(page)
    if build is None:
        return
    _run_dialog(page, _CPDialog(page, build), "Champion Points updated.")


def _edit_notes(page) -> None:
    build = _selected_build(page)
    if build is None:
        return
    _run_dialog(page, _NotesDialog(page, build), "Notes updated.")


def _edit_identity(page) -> None:
    build = _selected_build(page)
    if build is None:
        return
    _run_dialog(page, _IdentityDialog(page, build), "Build identity updated.")


def _context_variants_summary(page, build) -> FoundryCard:
    card = FoundryCard("Context Variants", "swapping")
    variants = list(getattr(build, "ContextVariants", ()) or ())
    if not variants:
        from models.build_model import BuildContextVariant
        variants = [
            BuildContextVariant.from_boss_loadout(item)
            for item in (getattr(build, "BossLoadouts", ()) or ())
        ]

    if variants:
        for variant in variants[:6]:
            kind = str(getattr(variant, "ContextType", "") or "Boss").strip()
            context = " • ".join(
                value
                for value in (
                    str(getattr(variant, "TeamName", "") or "").strip(),
                    str(getattr(variant, "BossName", "") or "").strip(),
                )
                if value
            ) or "Unspecified context"
            note = str(getattr(variant, "Notes", "") or "").strip()
            label = QLabel(f"{kind}: {context}" + (f" — {note}" if note else ""))
            label.setWordWrap(True)
            card.addWidget(label)
        if len(variants) > 6:
            card.addWidget(QLabel(f"+ {len(variants) - 6} more variant(s)"))
    else:
        card.addWidget(QLabel("No Team, Boss, or Team + Boss variants saved."))

    edit = FoundryButton("Edit Context Variants", role=ButtonRole.SECONDARY, compact=True)
    edit.clicked.connect(lambda: page._open_phase14_legacy_build_editor())
    card.addWidget(edit)
    return card


def _favorite_button(page, build) -> QPushButton:
    from ui import phase14_build_profile_support as profiles

    profile = profiles._profile(page, build)
    button = QPushButton("★" if profile.favorite else "☆")
    button.setToolTip("Remove from Favorites" if profile.favorite else "Add to Favorites")
    button.setProperty("favoriteAction", True)
    button.setFixedSize(38, 38)

    def toggle() -> None:
        build_id = profiles._build_id(page, build)
        if not build_id:
            return
        current = profiles._service().get(build_id)
        profiles._service().update(build_id, favorite=not current.favorite)
        profiles._populate_profile_table(page)
        page._refresh_detail()

    button.clicked.connect(toggle)
    return button


def _role_icon(role: str):
    value = str(role or "").strip().casefold()
    if "heal" in value:
        return _ROLE_ICONS["healer"]
    if "tank" in value:
        return _ROLE_ICONS["tank"]
    if "damage" in value or value in {"dd", "support dd"}:
        return _ROLE_ICONS["damage dealer"]
    return None


def _class_icon(class_name: str) -> QIcon:
    raw = str(class_name or "").strip()
    for name in (raw, raw.casefold(), raw.replace(" ", "-"), raw.casefold().replace(" ", "-")):
        value = semantic_icon(name)
        if not value.isNull():
            return value
    return QIcon()


def _header(page, build) -> QWidget:
    from ui import phase14_build_profile_support as profiles
    from ui import phase14_builds_command_center_support as command_center

    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(8, 7, 8, 7)
    layout.setSpacing(9)

    class_icon = _class_icon(build.EsoClass)
    class_label = QLabel()
    class_label.setFixedSize(34, 34)
    if not class_icon.isNull():
        class_label.setPixmap(class_icon.pixmap(QSize(32, 32)))
    layout.addWidget(class_label)

    text = QVBoxLayout()
    text.setSpacing(2)
    title = QLabel(f"{_text(build.Name, 'Unnamed Character')} — {_text(build.BuildName, 'Default')}")
    title.setProperty("heroTitle", True)
    text.addWidget(title)

    content = command_center._content_for_build(build)
    subtitle = QLabel("  •  ".join(value for value in (build.EsoClass, build.Role, content) if str(value or "").strip()))
    subtitle.setProperty("pageSubtitle", True)
    text.addWidget(subtitle)
    layout.addLayout(text, 1)

    layout.addWidget(_favorite_button(page, build))

    ready = QCheckBox("Ready")
    ready.setToolTip(
        "Mark this saved build as ready for raid. This is your own check, "
        "not a team or encounter check."
    )
    ready.setChecked(bool(getattr(build, "ReadyForRaid", False)))
    ready.toggled.connect(
        lambda checked, selected=build: page._set_build_ready(selected, checked)
    )
    layout.addWidget(ready)

    profile = profiles._profile(page, build)
    ownership = QLabel("My Build" if profile.ownership == "mine" else (profile.source_owner or "Team Build"))
    ownership.setProperty("cardBadge", True)
    layout.addWidget(ownership)

    edit = FoundryButton("", role=ButtonRole.SECONDARY, compact=True)
    edit.setFixedSize(38, 38)
    edit.setToolTip("Edit build identity")
    edit_icon = semantic_icon("pen")
    if not edit_icon.isNull():
        edit.setIcon(edit_icon)
        edit.setIconSize(QSize(18, 18))
    edit.clicked.connect(lambda: _edit_identity(page))
    layout.addWidget(edit)
    return host


def _baseline_strip(page, build) -> QWidget:
    from services.build_profile_service import build_profile_exception_count
    from ui import phase14_build_profile_support as profiles

    profile = profiles._profile(page, build)
    host = QWidget()
    host.setProperty("foundryCard", True)
    row = QHBoxLayout(host)
    row.setContentsMargins(10, 8, 10, 8)
    row.setSpacing(8)
    row.addWidget(icon_label("leather-armor", 22))
    label = QLabel(
        f"Endgame baseline: {profile.quality} • {profile.item_level} • {profile.enchantment_tier}"
    )
    row.addWidget(label, 1)
    exceptions = build_profile_exception_count(build, profile)
    warning = icon_label("warning", 18)
    row.addWidget(warning)
    count = QLabel(f"{exceptions} exception" + ("" if exceptions == 1 else "s"))
    count.setProperty("cardBadge", True)
    row.addWidget(count)
    edit = FoundryButton("›", role=ButtonRole.GHOST, compact=True)
    edit.setToolTip("Edit baseline")
    edit.clicked.connect(lambda: profiles._edit_baseline(page, build))
    row.addWidget(edit)
    return host


def _slot_values(value) -> GearSlot:
    return _gear_slot(value)


def _group_summary(rows: list[tuple[str, object]], page, build) -> tuple[str, str, int]:
    from ui import phase14_build_profile_support as profiles

    profile = profiles._profile(page, build)
    values = [(slot, _slot_values(value)) for slot, value in rows]
    populated = [(slot, value) for slot, value in values if not value.is_empty]
    sets = Counter(value.Set.strip() for _, value in populated if value.Set.strip())
    set_text = "  •  ".join(f"{name} ({count})" for name, count in sets.most_common()) or "Not configured"

    def common(field: str, fallback: str = "") -> str:
        items = [str(getattr(value, field, "") or "").strip() for _, value in populated]
        items = [item for item in items if item]
        if not items:
            return fallback
        counts = Counter(items)
        if len(counts) == 1:
            return next(iter(counts))
        return "Mixed"

    trait = common("Trait")
    enchant = common("Enchant")
    quality = common("Quality", profile.quality)
    tier = common("EnchantTier", profile.enchantment_tier)
    level = common("Level", profile.item_level)
    meta = "  |  ".join(value for value in (trait, enchant, tier or quality, level) if value)
    return set_text, meta, len(populated)


def _detail_rows(rows: list[tuple[str, object]]) -> QWidget:
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(8, 4, 8, 6)
    layout.setSpacing(3)
    for slot, raw in rows:
        value = _slot_values(raw)
        line = QWidget()
        row = QHBoxLayout(line)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(7)
        row.addWidget(icon_label(_SLOT_ICONS.get(slot, "leather-armor"), 18))
        row.addWidget(QLabel(slot))
        row.addStretch(1)
        summary_parts = [item for item in (value.Set, value.Enchant, value.WeaponType or value.Weight)
                         if str(item or "").strip()]
        if value.Trait:
            trait_icon = _trait_icon_name(value.Trait)
            if trait_icon:
                row.addWidget(icon_label(trait_icon, 16))
            summary_parts.insert(1 if summary_parts else 0, value.Trait)
        summary = " • ".join(summary_parts) or "Not configured"
        row.addWidget(QLabel(summary))
        layout.addWidget(line)
    host.hide()
    return host


def _gear_card(page, title: str, rows: list[tuple[str, object]]) -> FoundryCard:
    build = _selected_build(page)
    card_icon = {
        "Armor": "leather-armor",
        "Jewelry": "heart-necklace",
        "Front Bar": "crossed-swords",
        "Back Bar": "crossed-swords",
    }.get(title, "leather-armor")
    card = FoundryCard(title, card_icon)

    set_text, meta, count = _group_summary(rows, page, build)
    planned_sets = [
        str(value).strip()
        for value in (getattr(build, "PlannedGearSets", ()) or ())
        if str(value).strip()
    ]
    if count == 0 and planned_sets:
        set_text = " + ".join(planned_sets)
        meta = "Comp Maker plan • exact slots not assigned yet"

    header = QHBoxLayout()
    count_label = QLabel(f"{count} item" + ("" if count == 1 else "s"))
    count_label.setProperty("muted", True)
    header.addWidget(count_label)
    header.addStretch(1)
    edit = FoundryButton("Edit", role=ButtonRole.SECONDARY, compact=True)
    edit_icon = semantic_icon("pen")
    if not edit_icon.isNull():
        edit.setIcon(edit_icon)
        edit.setIconSize(QSize(16, 16))
    edit.clicked.connect(lambda: _edit_gear(page, title))
    header.addWidget(edit)

    detail = _detail_rows(rows)
    expand = FoundryButton("⌄", role=ButtonRole.GHOST, compact=True)
    expand.setFixedWidth(34)
    expand.clicked.connect(lambda: detail.setVisible(not detail.isVisible()))
    header.addWidget(expand)
    card.addLayout(header)

    primary = QLabel(set_text)
    primary.setWordWrap(True)
    card.addWidget(primary)
    if meta:
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)
        populated_traits = [
            _slot_values(value).Trait
            for _slot, value in rows
            if str(_slot_values(value).Trait or "").strip()
        ]
        if populated_traits:
            common_trait = Counter(populated_traits).most_common(1)[0][0]
            trait_icon = _trait_icon_name(common_trait)
            if trait_icon:
                meta_row.addWidget(icon_label(trait_icon, 17))
        secondary = QLabel(meta)
        secondary.setProperty("muted", True)
        secondary.setWordWrap(True)
        meta_row.addWidget(secondary, 1)
        card.addLayout(meta_row)
    card.addWidget(detail)
    return card


def _skills_tab(page, build) -> QWidget:
    from ui import phase14_build_icon_polish_support as icon_polish

    tab = QWidget()
    outer = QVBoxLayout(tab)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(8)

    planned_skills = [
        str(value).strip()
        for value in (getattr(build, "PlannedSkills", ()) or ())
        if str(value).strip()
    ]
    if planned_skills:
        planned_card = FoundryCard("Comp Planned Skills", "clipboard")
        note = QLabel(
            "Planned in Comp Maker. These are requirements/recommendations, not exact bar slots."
        )
        note.setWordWrap(True)
        note.setProperty("muted", True)
        planned_card.addWidget(note)
        planned = QLabel(", ".join(planned_skills))
        planned.setWordWrap(True)
        planned_card.addWidget(planned)
        outer.addWidget(planned_card)

    bars = QWidget()
    layout = QHBoxLayout(bars)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for title, values in (("Base Front Bar", build.FrontBarSkills), ("Base Back Bar", build.BackBarSkills)):
        card = FoundryCard(title, "lunar-wand")
        hint = QLabel("Context variants inherit these base skill bars until overridden.")
        hint.setProperty("muted", True)
        hint.setWordWrap(True)
        card.addWidget(hint)
        for index, skill in enumerate(values, start=1):
            card.addWidget(icon_polish._skill_row(index, skill))
        edit = FoundryButton("Edit Base Skills", role=ButtonRole.SECONDARY, compact=True)
        edit.clicked.connect(lambda: _edit_skills(page))
        card.addWidget(edit)
        layout.addWidget(card, 1)
    outer.addWidget(bars, 1)
    return tab


def _cp_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    card = FoundryCard("Base Champion Points", "progression")
    hint = QLabel("Context variants inherit these base Champion Points until overridden.")
    hint.setProperty("muted", True)
    hint.setWordWrap(True)
    card.addWidget(hint)
    entries = [entry for entry in build.ChampionPoints if str(entry.Name or "").strip()]
    if entries:
        for entry in entries:
            label = QLabel(f"{entry.Name}  {entry.Points}".strip())
            card.addWidget(label)
    else:
        card.addWidget(QLabel("No base Champion Points recorded."))
    edit = FoundryButton("Edit Base CP", role=ButtonRole.SECONDARY, compact=True)
    edit.clicked.connect(lambda: _edit_cp(page))
    card.addWidget(edit)
    layout.addWidget(card)
    layout.addStretch(1)
    return tab


def _consumables_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    card = FoundryCard("Consumables", "potion")
    for label, value, icon_name in (
        ("Food", _text(build.Food, "Not selected"), "food"),
        ("Potion", _text(build.Potion, "Not selected"), "potion"),
    ):
        row = QHBoxLayout()
        row.addWidget(icon_label(icon_name, 22))
        row.addWidget(QLabel(label))
        row.addStretch(1)
        row.addWidget(QLabel(value))
        card.addLayout(row)
    edit = FoundryButton("Edit Consumables", role=ButtonRole.SECONDARY, compact=True)
    edit.clicked.connect(lambda: _edit_consumables(page))
    card.addWidget(edit)
    layout.addWidget(card)
    layout.addStretch(1)
    return tab


def _notes_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    card = FoundryCard("Notes", "feather")
    note = QLabel(_text(build.Notes, "No build notes recorded."))
    note.setWordWrap(True)
    card.addWidget(note)
    edit = FoundryButton("Edit Notes", role=ButtonRole.SECONDARY, compact=True)
    edit.clicked.connect(lambda: _edit_notes(page))
    card.addWidget(edit)
    layout.addWidget(card)
    layout.addStretch(1)
    return tab


def _character_progression_dialog(page, build, *, tab_index: int = 0) -> None:
    """Open the character-owned passive/CP editor from the Phase 14 dossier."""
    from services.character_progression_service import CharacterProgressionService
    from ui.phase5_build_ui_support import CharacterProgressionDialog, _character_id_for_page

    character_id = _character_id_for_page(page, build)
    if not character_id:
        page.status.error("Character progression could not resolve a canonical character identity.")
        return

    catalog_service = page.build_service.canonical.catalog_service
    character = catalog_service.get_character(character_id)
    if character is None:
        page.status.error("Canonical character record was not found.")
        return

    dialog = CharacterProgressionDialog(
        reference=page.reference,
        character=character,
        parent=page,
    )
    tabs = dialog.findChild(QTabWidget)
    if tabs is not None and 0 <= int(tab_index) < tabs.count():
        tabs.setCurrentIndex(int(tab_index))

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    saved = CharacterProgressionService(catalog_service).save(
        character_id=character_id,
        owned_skill_lines=dialog.owned_skill_lines,
        passive_ranks=dialog.passive_ranks,
        passive_cp_points=dialog.passive_cp_points,
    )
    if saved is None:
        page.status.error("Character progression could not be saved.")
        return

    page.status.success("Character progression saved. All builds for this character share it.")
    page._refresh_detail()


def _progression_tab(page, build) -> QWidget:
    """Character-owned non-slotted progression beside the build-owned Skills/CP tabs."""
    from ui.phase5_build_ui_support import _character_id_for_page

    tab = QWidget()
    layout = QGridLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    character_id = _character_id_for_page(page, build)
    character = (
        page.build_service.canonical.catalog_service.get_character(character_id)
        if character_id
        else None
    ) or {}

    owned_lines = [
        str(value).strip()
        for value in character.get("owned_skill_lines", ())
        if str(value or "").strip()
    ]
    passive_ranks = {
        str(name).strip(): int(rank)
        for name, rank in dict(character.get("passive_ranks") or {}).items()
        if str(name or "").strip()
    }
    passive_cp = {
        str(name).strip(): int(points)
        for name, points in dict(character.get("passive_cp_points") or {}).items()
        if str(name or "").strip()
    }

    skills = FoundryCard("Passive Skills", "book-open-text")
    note = QLabel(
        "Character-owned skill-line access and purchased passive ranks. "
        "These apply to every build for this character and are not bar slots."
    )
    note.setWordWrap(True)
    note.setProperty("muted", True)
    skills.addWidget(note)
    skills.addWidget(QLabel(f"Unlocked optional skill lines: {len(owned_lines)}"))
    skills.addWidget(QLabel(f"Recorded passive ranks: {len(passive_ranks)}"))
    if owned_lines:
        preview = QLabel(" • ".join(owned_lines[:6]) + (" …" if len(owned_lines) > 6 else ""))
        preview.setWordWrap(True)
        skills.addWidget(preview)
    edit_skills = FoundryButton("Edit Passive Skills", role=ButtonRole.SECONDARY, compact=True)
    edit_skills.clicked.connect(lambda: _character_progression_dialog(page, build, tab_index=0))
    skills.addWidget(edit_skills)
    layout.addWidget(skills, 0, 0)

    cp = FoundryCard("Passive Champion Points", "progression")
    cp_note = QLabel(
        "Non-slottable Champion stars owned by the character. "
        "The normal CP tab remains the build-specific slotted Champion bar."
    )
    cp_note.setWordWrap(True)
    cp_note.setProperty("muted", True)
    cp.addWidget(cp_note)
    cp.addWidget(QLabel(f"Recorded passive Champion stars: {len(passive_cp)}"))
    if passive_cp:
        bought = sum(1 for points in passive_cp.values() if points > 0)
        cp.addWidget(QLabel(f"Purchased / ranked stars: {bought}"))
    edit_cp = FoundryButton("Edit Passive CP", role=ButtonRole.SECONDARY, compact=True)
    edit_cp.clicked.connect(lambda: _character_progression_dialog(page, build, tab_index=1))
    cp.addWidget(edit_cp)
    layout.addWidget(cp, 0, 1)

    layout.setColumnStretch(0, 1)
    layout.setColumnStretch(1, 1)
    layout.setRowStretch(1, 1)
    return tab


def _scribing_tab(page, build) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    card = FoundryCard("Scribing", "scroll-quill")
    recipes = tuple(getattr(build, "ScribedSkillRecipes", ()) or ())
    names = [str(getattr(recipe, "ResultName", "") or "").strip() for recipe in recipes]
    names = [name for name in names if name] or [
        str(name).strip() for name in getattr(build, "ScribedSkills", ()) or () if str(name).strip()
    ]
    if names:
        for name in names:
            card.addWidget(QLabel(name))
    else:
        card.addWidget(QLabel("No scribed skills recorded."))
    edit = FoundryButton("Edit Scribing", role=ButtonRole.SECONDARY, compact=True)
    existing = getattr(page, "_edit_scribed_skills", None)
    if callable(existing):
        edit.clicked.connect(existing)
    else:
        edit.clicked.connect(lambda: page.build_tabs.setCurrentIndex(3))
    card.addWidget(edit)
    layout.addWidget(card)
    layout.addStretch(1)
    return tab


def _proxy(page, name: str) -> None:
    button = getattr(page, name, None)
    if button is not None:
        button.click()


def _footer(page) -> QWidget:
    host = QWidget()
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 4, 0, 0)
    row.setSpacing(8)

    more = QToolButton()
    more.setText("⋯  More actions")
    more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    more.setProperty("secondary", True)
    menu = QMenu(more)

    actions = (
        ("Save as Template", lambda: _proxy(page, "template_build_button")),
        ("Copy Build To…", lambda: _proxy(page, "copy_build_button")),
        ("Export Builds…", page._export_csv),
        ("Delete Build", lambda: _proxy(page, "delete_build_button")),
    )
    for label, callback in actions:
        action = QAction(label, menu)
        action.triggered.connect(callback)
        menu.addAction(action)
    more.setMenu(menu)
    row.addWidget(more)
    row.addStretch(1)

    save = FoundryButton("Save", role=ButtonRole.SUCCESS)
    save.setMinimumWidth(190)
    save.setMinimumHeight(42)
    save_icon = semantic_icon("check-mark")
    if not save_icon.isNull():
        save.setIcon(save_icon)
        save.setIconSize(QSize(18, 18))
    save.setStyleSheet(
        "QPushButton { background: #C8A46A; color: #0C171B; border: 1px solid #E0C27A; "
        "border-radius: 6px; padding: 8px 18px; font-weight: 700; }"
        "QPushButton:hover { background: #D8B86F; }"
    )
    save.clicked.connect(page._save)
    row.addWidget(save)
    return host


def _install_overrides() -> None:
    from ui import phase14_build_inspector_support as inspector
    from ui import phase14_build_profile_support as profiles

    inspector._header = _header
    original_overview = inspector._overview_tab

    def overview_with_context_variants(page, build):
        tab = original_overview(page, build)
        layout = tab.layout()
        if isinstance(layout, QGridLayout):
            layout.addWidget(_context_variants_summary(page, build), 2, 0, 1, 2)
            layout.setRowStretch(3, 1)
        return tab

    inspector._overview_tab = overview_with_context_variants
    inspector._gear_card = _gear_card
    inspector._skills_tab = _skills_tab
    inspector._cp_tab = _cp_tab
    inspector._progression_tab = _progression_tab
    inspector._consumables_tab = _consumables_tab
    inspector._scribing_tab = _scribing_tab
    inspector._notes_tab = _notes_tab
    inspector._footer = _footer
    profiles._baseline_card = _baseline_strip


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    _install_overrides()

    from ui.builds_page import BuildsPage

    original_edit_selected = BuildsPage._edit_selected

    def edit_selected_phase14(self) -> None:
        # Normal Phase 14 editing is intentionally focused. Keep the legacy
        # monolithic editor reachable only as an explicit compatibility fallback.
        _edit_identity(self)

    def open_phase14_legacy_build_editor(self) -> None:
        """Explicit escape hatch for the superseded monolithic editor."""
        tabs = getattr(self, "build_tabs", None)
        if tabs is None or tabs.count() <= 1:
            return
        tabs.setTabVisible(1, True)
        self._phase14_legacy_edit_selected()

    BuildsPage._phase14_legacy_edit_selected = original_edit_selected
    BuildsPage._open_phase14_legacy_build_editor = open_phase14_legacy_build_editor
    BuildsPage._edit_selected = edit_selected_phase14
    _INSTALLED = True


__all__ = ["install"]
