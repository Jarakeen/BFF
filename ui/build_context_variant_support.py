from __future__ import annotations

"""Upgrade legacy boss alternates into sparse team/boss context variants."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from engine.config import get_data_dir
from models.build_model import (
    ARMOR_SLOTS,
    ARMOR_TRAITS,
    JEWELRY_TRAITS,
    MUNDUS_CHOICES,
    WEAPON_TRAITS,
    BossLoadout,
    BuildContextVariant,
    GearSlot,
)
from services.eso_database import EsoDatabase
from services.roster_service import RosterService
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from widgets import build_editor as build_editor_module


_INSTALLED = False


def _team_names() -> list[str]:
    try:
        service = RosterService(EsoDatabase(get_data_dir() / "eso.db"))
        return service.list_team_names()
    except Exception:
        return []


def _editable_combo(values) -> QComboBox:
    combo = QComboBox()
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.addItem("")
    combo.addItems([str(value) for value in values if str(value or "").strip()])
    combo.setMinimumHeight(28)
    return combo


class ContextVariantCard(FoundryCard):
    """One sparse override row over a complete parent build."""

    removeRequested = Signal(object)

    def __init__(self, editor, parent=None):
        super().__init__("Context Variant", parent=parent)
        self.editor = editor

        self.context_type = QComboBox()
        self.context_type.addItems(["Team", "Boss", "Team + Boss"])
        self.team_name = _editable_combo(_team_names())
        self.boss_name = QLineEdit()
        self.form_override = QComboBox()
        self.mundus = _editable_combo(MUNDUS_CHOICES[1:])
        self.second_mundus = _editable_combo(MUNDUS_CHOICES[1:])
        self.front_bar = build_editor_module.SkillBarRow(editor.skill_choices)
        self.back_bar = build_editor_module.SkillBarRow(editor.skill_choices)
        self.cp_grid = build_editor_module.ChampionPointGrid(editor.cp_choices)
        self.food = _editable_combo(editor.food_choices)
        self.potion = _editable_combo(editor.potion_choices)
        self.notes = QLineEdit()

        self._refresh_form_choices()
        self.form_override.currentIndexChanged.connect(lambda *_: self._sync_skill_context())
        for toggle_name in ("werewolf", "vampire"):
            toggle = getattr(editor, toggle_name, None)
            if toggle is not None and hasattr(toggle, "toggled"):
                toggle.toggled.connect(lambda *_: self._on_affiliation_changed())

        remove = FoundryButton("Remove", role=ButtonRole.DANGER, compact=True)
        remove.clicked.connect(lambda: self.removeRequested.emit(self))
        self.set_header_action(remove)

        hint = QLabel(
            "Leave fields blank to inherit from the base build. "
            "Resolution order: Team + Boss → Team → Boss → Base. "
            "Form Override is separate from affiliation: Werewolf/Vampire choices only appear when the base character has that affiliation. "
            "Raid assignments stay on the team Assignments surface."
        )
        hint.setWordWrap(True)
        hint.setProperty("muted", True)
        self.addWidget(hint)

        context_form = QFormLayout()
        context_form.addRow("Variant Type", self.context_type)
        context_form.addRow("Team", self.team_name)
        context_form.addRow("Boss / Encounter", self.boss_name)
        context_form.addRow("Form Override", self.form_override)
        self.addLayout(context_form)

        self.gear_rows = {}
        gear_card = FoundryCard("Gear Overrides")
        gear_grid = QGridLayout()
        gear_grid.setHorizontalSpacing(6)
        gear_grid.setVerticalSpacing(3)
        headers = ["Slot", "Set 1", "Set 2", "Quality", "Trait", "Weight / Weapon", "Enchant", "Tier", "Level"]
        for column, text in enumerate(headers):
            label = QLabel(text)
            label.setStyleSheet("font-weight:700;")
            gear_grid.addWidget(label, 0, column)

        specs = [
            *((slot, slot, True, False) for slot in ARMOR_SLOTS),
            ("Neck", "Necklace", False, False),
            ("Ring1", "Ring 1", False, False),
            ("Ring2", "Ring 2", False, False),
            ("front_main_hand", "Front Main Hand", False, True),
            ("front_off_hand", "Front Off Hand", False, True),
            ("back_main_hand", "Back Main Hand", False, True),
            ("back_off_hand", "Back Off Hand", False, True),
        ]
        for row_number, (key, label, armor, weapon) in enumerate(specs, 1):
            traits = ARMOR_TRAITS if armor else JEWELRY_TRAITS if key in {"Neck", "Ring1", "Ring2"} else WEAPON_TRAITS
            weapon_types = build_editor_module.OFFHAND_WEAPON_TYPES if key.endswith("off_hand") else None
            row = build_editor_module.GearSlotRow(
                editor.set_choices,
                traits,
                armor=armor,
                weapon=weapon,
                weapon_types=weapon_types,
            )
            self.gear_rows[key] = row
            gear_grid.addWidget(QLabel(label), row_number, 0)
            for column, widget in enumerate(
                [
                    row.set_combo,
                    row.set2_combo,
                    row.quality_combo,
                    row.trait_combo,
                    row.type_combo,
                    row.enchant_combo,
                    row.enchant_tier_combo,
                    row.level_combo,
                ],
                1,
            ):
                gear_grid.addWidget(widget, row_number, column)

        gear_card.addLayout(gear_grid)
        self.addWidget(gear_card)

        build_form = QFormLayout()
        build_form.addRow("Mundus", self.mundus)
        build_form.addRow("Second Mundus", self.second_mundus)
        build_form.addRow("Front Bar Overrides", self.front_bar)
        build_form.addRow("Back Bar Overrides", self.back_bar)
        cp_hint = QLabel("Any CP entries here replace the base slotted CP set for this context.")
        cp_hint.setProperty("muted", True)
        cp_wrap = QVBoxLayout()
        cp_wrap.addWidget(cp_hint)
        cp_wrap.addWidget(self.cp_grid)
        build_form.addRow("CP Override", cp_wrap)
        consumables = QHBoxLayout()
        consumables.addWidget(QLabel("Food"))
        consumables.addWidget(self.food, 1)
        consumables.addWidget(QLabel("Potion"))
        consumables.addWidget(self.potion, 1)
        build_form.addRow("Consumables", consumables)
        build_form.addRow("Notes", self.notes)
        self.addLayout(build_form)

    def _affiliations(self) -> tuple[bool, bool]:
        vampire_toggle = getattr(self.editor, "vampire", None)
        werewolf_toggle = getattr(self.editor, "werewolf", None)
        vampire = bool(vampire_toggle is not None and vampire_toggle.isChecked())
        werewolf = bool(werewolf_toggle is not None and werewolf_toggle.isChecked())
        return vampire, werewolf

    def _refresh_form_choices(self, preferred: str | None = None) -> None:
        current = str(preferred if preferred is not None else self.form_override.currentData() or "").strip().casefold()
        vampire, werewolf = self._affiliations()
        self.form_override.blockSignals(True)
        self.form_override.clear()
        self.form_override.addItem("Base / Normal", "")
        if werewolf:
            self.form_override.addItem("Werewolf", "werewolf")
        if vampire:
            self.form_override.addItem("Vampire", "vampire")
        index = self.form_override.findData(current)
        self.form_override.setCurrentIndex(index if index >= 0 else 0)
        self.form_override.blockSignals(False)

    def _on_affiliation_changed(self) -> None:
        self._refresh_form_choices()
        self._sync_skill_context()

    def _sync_skill_context(self, eso_class: str | None = None) -> None:
        """Give variant bars explicit parent affiliation and transformed-form state."""
        selected_class = (
            str(eso_class or "").strip()
            or str(getattr(getattr(self.editor, "eso_class", None), "currentText", lambda: "")()).strip()
        )
        vampire, werewolf = self._affiliations()
        transformed_form = str(self.form_override.currentData() or "").strip().casefold() or None

        for bar in (self.front_bar, self.back_bar):
            if hasattr(bar, "set_class"):
                bar.set_class(selected_class)
            if hasattr(bar, "set_affiliation"):
                bar.set_affiliation(vampire=vampire, werewolf=werewolf)
            if hasattr(bar, "set_form"):
                bar.set_form(transformed_form)

    def set_class(self, eso_class: str) -> None:
        self._sync_skill_context(eso_class)

    @staticmethod
    def _sparse_armor(rows) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for slot in ARMOR_SLOTS:
            value = rows[slot].value
            if not value.is_empty:
                result[slot] = value.to_dict()
        return result

    @property
    def value(self) -> BuildContextVariant:
        return BuildContextVariant(
            ContextType=self.context_type.currentText().strip() or "Boss",
            TeamName=self.team_name.currentText().strip(),
            BossName=self.boss_name.text().strip(),
            TransformedForm=str(self.form_override.currentData() or "").strip().casefold(),
            Mundus=self.mundus.currentText().strip(),
            SecondMundus=self.second_mundus.currentText().strip(),
            Armor=self._sparse_armor(self.gear_rows),
            FrontBarWeapon=self.gear_rows["front_main_hand"].value,
            FrontBarOffHand=self.gear_rows["front_off_hand"].value,
            BackBarWeapon=self.gear_rows["back_main_hand"].value,
            BackBarOffHand=self.gear_rows["back_off_hand"].value,
            Necklace=self.gear_rows["Neck"].value,
            Ring1=self.gear_rows["Ring1"].value,
            Ring2=self.gear_rows["Ring2"].value,
            ChampionPoints=self.cp_grid.value,
            FrontBarSkills=self.front_bar.value,
            BackBarSkills=self.back_bar.value,
            Food=self.food.currentText().strip(),
            Potion=self.potion.currentText().strip(),
            Notes=self.notes.text().strip(),
        )

    def load(self, variant) -> None:
        if isinstance(variant, BossLoadout):
            variant = BuildContextVariant.from_boss_loadout(variant)
        self.context_type.setCurrentText(variant.ContextType or "Boss")
        self.team_name.setCurrentText(variant.TeamName)
        self.boss_name.setText(variant.BossName)
        self._refresh_form_choices(getattr(variant, "TransformedForm", ""))
        self.mundus.setCurrentText(variant.Mundus)
        self.second_mundus.setCurrentText(variant.SecondMundus)

        for slot in ARMOR_SLOTS:
            self.gear_rows[slot].load(GearSlot.from_dict(variant.Armor.get(slot, {})))
        self.gear_rows["front_main_hand"].load(variant.FrontBarWeapon)
        self.gear_rows["front_off_hand"].load(variant.FrontBarOffHand)
        self.gear_rows["back_main_hand"].load(variant.BackBarWeapon)
        self.gear_rows["back_off_hand"].load(variant.BackBarOffHand)
        self.gear_rows["Neck"].load(variant.Necklace)
        self.gear_rows["Ring1"].load(variant.Ring1)
        self.gear_rows["Ring2"].load(variant.Ring2)

        self._sync_skill_context()
        self.cp_grid.load_entries(variant.ChampionPoints)
        self.front_bar.load(variant.FrontBarSkills)
        self.back_bar.load(variant.BackBarSkills)
        self.food.setCurrentText(variant.Food)
        self.potion.setCurrentText(variant.Potion)
        self.notes.setText(variant.Notes)


def _build_variants_card(self):
    card = FoundryCard("Context Variants")
    body = QVBoxLayout()
    self.boss_container = QVBoxLayout()
    body.addLayout(self.boss_container)

    actions = QHBoxLayout()
    actions.setSpacing(8)
    add_variant = FoundryButton("+ ADD VARIANT", role=ButtonRole.PRIMARY, compact=False)
    add_variant.setMinimumHeight(42)
    add_variant.setToolTip(
        "Add a Team, Boss, or Team + Boss override that inherits unchanged fields from this build."
    )
    add_variant.setStyleSheet(
        "QPushButton { background-color: #D1983D; color: #0C171B; "
        "border: 1px solid #F3D28A; border-radius: 6px; "
        "font-weight: 800; padding: 8px 18px; } "
        "QPushButton:hover { background-color: #E7B75E; } "
        "QPushButton:pressed { background-color: #B98027; }"
    )
    add_build = FoundryButton("+ Add New Build", role=ButtonRole.SECONDARY, compact=True)
    save = FoundryButton("Save This Build", role=ButtonRole.SUCCESS, compact=False)
    cancel = FoundryButton("Cancel", role=ButtonRole.DANGER, compact=False)
    save.setMinimumWidth(150)
    cancel.setMinimumWidth(110)
    save.setToolTip("Save all changes to this build.")
    cancel.setToolTip("Discard unsaved changes and reload the saved build.")

    add_variant.clicked.connect(self.add_boss_loadout)
    add_build.clicked.connect(self._handle_add_build)
    save.clicked.connect(self.saveRequested.emit)
    cancel.clicked.connect(self.cancelRequested.emit)

    actions.addWidget(add_variant)
    actions.addStretch()
    actions.addWidget(add_build)
    actions.addWidget(save)
    actions.addWidget(cancel)
    body.addLayout(actions)
    card.addLayout(body)

    self.add_context_variant_button = add_variant
    self.save_build_button = save
    self.cancel_build_button = cancel
    return card


def _add_variant(self, variant=None):
    card = ContextVariantCard(self)
    card.set_class(self.eso_class.currentText().strip())
    card.removeRequested.connect(self._remove_boss_loadout)
    self._boss_cards.append(card)
    self.boss_container.addWidget(card)
    if variant is not None:
        card.load(variant)
    return card


def _variants_summary_card(self, build):
    card = FoundryCard("Context Variants")
    variants = list(getattr(build, "ContextVariants", ()) or ())
    if not variants:
        variants = [BuildContextVariant.from_boss_loadout(item) for item in build.BossLoadouts]
    if not variants:
        card.addWidget(QLabel("No team or boss variants saved."))
        return card

    for variant in variants:
        kind = str(variant.ContextType or "Boss").strip()
        context_bits = []
        if variant.TeamName:
            context_bits.append(variant.TeamName)
        if variant.BossName:
            context_bits.append(variant.BossName)
        context = " • ".join(context_bits) or "Unspecified context"
        form = str(getattr(variant, "TransformedForm", "") or "").strip().title()
        form_note = f" • {form} form" if form else ""
        notes = f" — {variant.Notes}" if variant.Notes else ""
        card.addWidget(QLabel(f"{kind}: {context}{form_note}{notes}"))
    return card


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    BuildEditor = build_editor_module.BuildEditor
    original_model = BuildEditor.model.fget
    original_load = BuildEditor.load

    def model_with_context_variants(self):
        model = original_model(self)
        model.ContextVariants = [card.value for card in self._boss_cards]
        model.BossLoadouts = []
        return model

    def load_with_context_variants(self, model):
        original_load(self, model)
        for card in list(self._boss_cards):
            self._remove_boss_loadout(card)
        variants = list(getattr(model, "ContextVariants", ()) or ())
        if not variants:
            variants = [BuildContextVariant.from_boss_loadout(item) for item in model.BossLoadouts]
        for variant in variants:
            self.add_boss_loadout(variant)

    BuildEditor._build_boss_card = _build_variants_card
    BuildEditor.add_boss_loadout = _add_variant
    BuildEditor.model = property(model_with_context_variants)
    BuildEditor.load = load_with_context_variants

    from ui.builds_page import BuildsPage

    BuildsPage._alternates_card = _variants_summary_card
    _INSTALLED = True


__all__ = ["ContextVariantCard", "install"]
