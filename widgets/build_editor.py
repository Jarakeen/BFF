# widgets/build_editor.py
#
# Editable character build for one raid team member:
# identity, image, race/class, gear, CP, skill bars, food
# and potion, plus a scrolling list of boss alternate
# loadouts for the trial. Holds no persistence of its own
# -- the page reads/writes `model` and calls load()/clear(),
# same convention as widgets/roster_record.py.

from __future__ import annotations
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGridLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QLabel,
    QFileDialog,
    QFrame,
)
from widgets.gear_slot_tile import GearSlotTile
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_button import ButtonRole, FoundryButton
from services.eso_icon_resolver import EsoIconResolver
from models.build_model import (
    PlayerBuild,
    BossLoadout,
    GearSlot,
    ChampionPointEntry,
    ARMOR_SLOTS,
    ARMOR_TRAITS,
    WEAPON_TRAITS,
    JEWELRY_TRAITS,
)
from models.roster_model import ESO_CLASSES


class GearSlotRow(QWidget):
    """Reusable editor for one armor, weapon, or jewelry slot."""

    def __init__(
        self,
        set_choices: list[str],
        trait_choices: list[str],
        *,
        armor: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self.armor = armor

        # Set
        self.set_combo = QComboBox()
        self.set_combo.setEditable(True)
        self.set_combo.addItem("")
        self.set_combo.addItems(set_choices)

        # Trait
        self.trait_combo = QComboBox()
        self.trait_combo.addItem("")
        self.trait_combo.addItems(trait_choices)

        # Enchantment
        self.enchant_combo = QComboBox()
        self.enchant_combo.setEditable(True)
        self.enchant_combo.addItem("")

        # Weight, armor only
        self.weight_combo = QComboBox()

        if self.armor:
            self.weight_combo.addItems(
                [
                    "",
                    "Light",
                    "Medium",
                    "Heavy",
                ]
            )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(self.set_combo, 2)
        layout.addWidget(self.trait_combo, 1)
        layout.addWidget(self.enchant_combo, 1)

        if self.armor:
            layout.addWidget(self.weight_combo, 1)

    @property
    def value(self) -> GearSlot:
        return GearSlot(
            Set=self.set_combo.currentText().strip(),
            Trait=self.trait_combo.currentText().strip(),
            Enchant=self.enchant_combo.currentText().strip(),
            Weight=(
                self.weight_combo.currentText().strip()
                if self.armor
                else ""
            ),
        )

    def load(self, slot: GearSlot):
        self.set_combo.setCurrentText(slot.Set or "")
        self.trait_combo.setCurrentText(slot.Trait or "")
        self.enchant_combo.setCurrentText(slot.Enchant or "")

        if self.armor:
            self.weight_combo.setCurrentText(slot.Weight or "")

    def clear(self):
        self.set_combo.setCurrentText("")
        self.trait_combo.setCurrentText("")
        self.enchant_combo.setCurrentText("")

        if self.armor:
            self.weight_combo.setCurrentText("")


class SkillBarRow(QWidget):
    """5 active skills + 1 ultimate, displayed as clickable ESO skill tiles."""

    def __init__(self, skill_choices: list[str], parent=None):
        super().__init__(parent)

        self.fields: list[QComboBox] = []
        self.icon_resolver = EsoIconResolver()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for i in range(6):
            field = QComboBox()

            field.setEditable(True)
            field.addItem("")
            field.addItems(skill_choices)

            if i == 5:
                field.setToolTip("Ultimate")
            else:
                field.setToolTip(f"Skill {i + 1}")

            # Make the control large enough to display an ESO icon.
            field.setMinimumSize(72, 72)

            # Keep the text field functional, but give the control
            # a more compact skill-slot appearance.
            field.setIconSize(QSize(56, 56))

            self.fields.append(field)
            layout.addWidget(field)

            field.currentTextChanged.connect(
                lambda text, combo=field: self._update_icon(combo, text)
            )

    def _update_icon(
        self,
        field: QComboBox,
        skill_name: str,
    ) -> None:
        """Update the selected skill icon."""

        skill_name = skill_name.strip()

        # QComboBox does not support setIcon().
        # Skill icons are handled by the compact skill tile UI,
        # so there is nothing to clear or set on the combo itself.
        if not skill_name:
            return

    

        # For now, skill_choices contain names rather than full skill
        # records. The resolver needs the ESO texture path, so this
        # intentionally remains a safe no-op until we connect the
        # existing skill data to the row.
        #
        # The next step will supply the actual texture path here.
        return

    @property
    def value(self) -> list[str]:
        return [f.currentText().strip() for f in self.fields]

    def load(self, skills: list[str]):
        skills = list(skills) + [""] * 6

        for field, value in zip(self.fields, skills[:6]):
            field.setCurrentText(value)

    def clear(self):
        for field in self.fields:
            field.setCurrentText("")


class BossLoadoutCard(FoundryCard):
    """One alternate loadout for a specific boss in the trial."""

    removeRequested = Signal(object)

    def __init__(self, skill_choices: list[str], parent=None):
        super().__init__("Boss Alternate", parent=parent)

        self.boss_name = QLineEdit()
        self.boss_name.setPlaceholderText("Boss name")

        self.front_bar = SkillBarRow(skill_choices)
        self.back_bar = SkillBarRow(skill_choices)

        self.food = QLineEdit()
        self.potion = QLineEdit()

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Positioning, timing, anything that changes for this pull...")
        self.notes.setFixedHeight(60)

        remove_button = FoundryButton(
            "Remove Alternate",
            role=ButtonRole.DANGER,
            compact=True,
        )

        remove_button.clicked.connect(
            lambda: self.removeRequested.emit(self)
        )

        self.set_header_action(remove_button)

        form = QFormLayout()

        form.addRow("Boss", self.boss_name)
        form.addRow("Front Bar", self.front_bar)
        form.addRow("Back Bar", self.back_bar)

        consumables = QHBoxLayout()

        consumables.addWidget(QLabel("Food"))
        consumables.addWidget(self.food)
        consumables.addWidget(QLabel("Potion"))
        consumables.addWidget(self.potion)

        form.addRow("Consumables", consumables)
        form.addRow("Notes", self.notes)

        self.addLayout(form)

        self.boss_name.textChanged.connect(self._sync_title)

    def _sync_title(self):

        self.set_title(self.boss_name.text().strip() or "Boss Alternate")

    @property
    def value(self) -> BossLoadout:

        return BossLoadout(
            BossName=self.boss_name.text().strip(),
            FrontBarSkills=self.front_bar.value,
            BackBarSkills=self.back_bar.value,
            Food=self.food.text().strip(),
            Potion=self.potion.text().strip(),
            Notes=self.notes.toPlainText().strip(),
        )

    def load(self, loadout: BossLoadout):

        self.boss_name.setText(loadout.BossName)
        self.front_bar.load(loadout.FrontBarSkills)
        self.back_bar.load(loadout.BackBarSkills)
        self.food.setText(loadout.Food)
        self.potion.setText(loadout.Potion)
        self.notes.setPlainText(loadout.Notes)

        self._sync_title()


class ChampionPointRow(QWidget):

    removeRequested = Signal(object)

    def __init__(self, cp_choices: list[str], parent=None):
        super().__init__(parent)

        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.addItem("")
        self.name_combo.addItems(cp_choices)

        self.points = QLineEdit()
        self.points.setPlaceholderText("Points")
        self.points.setFixedWidth(70)

        remove_button = FoundryButton(
            "✕",
            role=ButtonRole.GHOST,
            compact=True,
        )

        remove_button.setFixedWidth(28)

        remove_button.clicked.connect(
            lambda: self.removeRequested.emit(self)
        )

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.name_combo, 3)
        layout.addWidget(self.points, 1)
        layout.addWidget(remove_button)

    @property
    def value(self) -> ChampionPointEntry:

        return ChampionPointEntry(
            Name=self.name_combo.currentText().strip(),
            Points=self.points.text().strip(),
        )

    def load(self, entry: ChampionPointEntry):

        self.name_combo.setCurrentText(entry.Name)
        self.points.setText(entry.Points)


class BuildEditor(QWidget):
    """
    Full editable build for one raid team member.

    Meant to sit inside a QScrollArea (the page provides
    that) -- this widget lays everything out vertically and
    does not scroll itself.
    """

    nameChanged = Signal(str)
    saveRequested = Signal()
    cancelRequested = Signal()

    def __init__(
        self,
        race_choices: list[str] | None = None,
        set_choices: list[str] | None = None,
        skill_choices: list[str] | None = None,
        cp_choices: list[str] | None = None,
        food_choices: list[str] | None = None,
        potion_choices: list[str] | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.race_choices = race_choices or []
        self.set_choices = set_choices or []
        self.skill_choices = skill_choices or []
        self.cp_choices = cp_choices or []
        self.food_choices = food_choices or []
        self.potion_choices = potion_choices or []
        self.image_path = ""

        self._cp_rows: list[ChampionPointRow] = []
        self._boss_cards: list[BossLoadoutCard] = []

        self.build_ui()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(12)

        root.addWidget(self._build_identity_card())
        root.addWidget(self._build_gear_card())
        root.addWidget(self._build_cp_card())
        root.addWidget(self._build_skills_card())

        self.boss_container = QVBoxLayout()

        self.boss_container.setSpacing(10)

        boss_card = FoundryCard("Boss Alternates")

        boss_card_body = QVBoxLayout()

        boss_card_body.addLayout(self.boss_container)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        add_boss_button = FoundryButton(
            "+ Add Boss Alternate",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        add_boss_button.clicked.connect(self.add_boss_loadout)
        button_row.addWidget(add_boss_button)

        button_row.addStretch(1)

        cancel_button = FoundryButton(
            "Cancel",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        save_button = FoundryButton(
            "Save This Build",
            role=ButtonRole.PRIMARY,
            compact=True,
        )

        cancel_button.clicked.connect(self.cancelRequested.emit)
        save_button.clicked.connect(self.saveRequested.emit)

        button_row.addWidget(cancel_button)
        button_row.addWidget(save_button)

        boss_card_body.addLayout(button_row)

        root.addWidget(boss_card)

        root.addStretch()

    def _build_identity_card(self) -> FoundryCard:

        card = FoundryCard("Identity")

        self.name = QLineEdit()
        self.name.setPlaceholderText("Character name")
        self.name.textChanged.connect(self.nameChanged.emit)

        self.gamertag = QLineEdit()
        self.gamertag.setPlaceholderText("@Gamertag")

        self.race = QComboBox()
        self.race.setEditable(True)
        self.race.addItem("")
        self.race.addItems(self.race_choices)

        self.eso_class = QComboBox()
        self.eso_class.addItems(ESO_CLASSES)

        self.notes = QTextEdit()
        self.notes.setFixedHeight(50)
        self.notes.setPlaceholderText("General notes about this build...")

        self.image_label = QLabel("No image")
        self.image_label.setFixedSize(96, 96)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFrameShape(QFrame.Shape.Box)
        self.image_label.setScaledContents(True)

        image_button = FoundryButton(
            "Choose Image...",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        image_button.clicked.connect(self.choose_image)

        clear_image_button = FoundryButton(
            "Clear",
            role=ButtonRole.GHOST,
            compact=True,
        )

        clear_image_button.clicked.connect(self.clear_image)

        image_buttons = QVBoxLayout()

        image_buttons.addWidget(image_button)
        image_buttons.addWidget(clear_image_button)
        image_buttons.addStretch()

        image_row = QHBoxLayout()

        image_row.addWidget(self.image_label)
        image_row.addLayout(image_buttons)
        image_row.addStretch()

        form = QFormLayout()

        form.addRow("Name", self.name)
        form.addRow("Gamertag", self.gamertag)
        form.addRow("Race", self.race)
        form.addRow("Class", self.eso_class)
        form.addRow("Notes", self.notes)

        content = QHBoxLayout()

        content.addLayout(form, 2)
        content.addLayout(image_row, 1)

        card.addLayout(content)

        return card

    def _build_gear_card(self) -> FoundryCard:
        card = FoundryCard("Gear")

        grid = QGridLayout()
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        self.armor_rows: dict[str, GearSlotRow] = {}
        self.gear_tiles: dict[str, GearSlotTile] = {}

        def add_armor_tile(
            slot: str,
            label: str,
            row: int,
            column: int,
        ) -> None:
            editor = GearSlotRow(
                self.set_choices,
                ARMOR_TRAITS,
                armor=True,
            )

            self.armor_rows[slot] = editor

            tile = GearSlotTile(
                slot=slot,
                label=label,
                editor=editor,
            )

            self.gear_tiles[slot] = tile

            grid.addWidget(
                tile,
                row,
                column,
                Qt.AlignmentFlag.AlignCenter,
            )

        # --------------------------------------------------
        # Armor silhouette
        # --------------------------------------------------

        add_armor_tile(
            "Head",
            "Head",
            0,
            1,
        )

        add_armor_tile(
            "Shoulders",
            "Shoulders",
            1,
            0,
        )

        add_armor_tile(
            "Chest",
            "Chest",
            1,
            1,
        )

        add_armor_tile(
            "Legs",
            "Legs",
            1,
            2,
        )

        add_armor_tile(
            "Hands",
            "Hands",
            2,
            0,
        )

        add_armor_tile(
            "Waist",
            "Waist",
            2,
            1,
        )

        add_armor_tile(
            "Feet",
            "Feet",
            2,
            2,
        )

        # --------------------------------------------------
        # Jewelry
        # --------------------------------------------------

        self.necklace = GearSlotRow(
            self.set_choices,
            JEWELRY_TRAITS,
        )

        self.ring1 = GearSlotRow(
            self.set_choices,
            JEWELRY_TRAITS,
        )

        self.ring2 = GearSlotRow(
            self.set_choices,
            JEWELRY_TRAITS,
        )

        jewelry = [
            (
                "Neck",
                "Neck",
                self.necklace,
                3,
                0,
            ),
            (
                "Ring1",
                "Ring 1",
                self.ring1,
                3,
                1,
            ),
            (
                "Ring2",
                "Ring 2",
                self.ring2,
                3,
                2,
            ),
        ]

        for slot, label, editor, row, column in jewelry:
            tile = GearSlotTile(
                slot=slot,
                label=label,
                editor=editor,
            )

            self.gear_tiles[slot] = tile

            grid.addWidget(
                tile,
                row,
                column,
                Qt.AlignmentFlag.AlignCenter,
            )

        # --------------------------------------------------
        # Weapons
        # --------------------------------------------------

        self.front_bar_weapon = GearSlotRow(
            self.set_choices,
            WEAPON_TRAITS,
        )

        self.back_bar_weapon = GearSlotRow(
            self.set_choices,
            WEAPON_TRAITS,
        )

        front_tile = GearSlotTile(
            slot="main_hand",
            label="Front Bar",
            editor=self.front_bar_weapon,
        )

        back_tile = GearSlotTile(
            slot="off_hand",
            label="Back Bar",
            editor=self.back_bar_weapon,
        )

        self.gear_tiles["main_hand"] = front_tile
        self.gear_tiles["off_hand"] = back_tile

        grid.addWidget(
            front_tile,
            4,
            0,
            1,
            2,
            Qt.AlignmentFlag.AlignCenter,
        )

        grid.addWidget(
            back_tile,
            4,
            2,
            1,
            1,
            Qt.AlignmentFlag.AlignCenter,
        )

        # --------------------------------------------------
        # Keep the grid compact
        # --------------------------------------------------

        for column in range(3):
            grid.setColumnStretch(column, 0)

        card.addLayout(grid)

        return card

    def _build_cp_card(self) -> FoundryCard:

        card = FoundryCard("Champion Points")

        self.cp_container = QVBoxLayout()

        self.cp_container.setSpacing(4)

        card.addLayout(self.cp_container)

        add_cp_button = FoundryButton(
            "+ Add CP Star",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        add_cp_button.clicked.connect(self.add_cp_row)

        add_cp_row = QHBoxLayout()

        add_cp_row.addWidget(add_cp_button)
        add_cp_row.addStretch()

        card.addLayout(add_cp_row)

        return card

    def _build_skills_card(self) -> FoundryCard:

        card = FoundryCard("Skills & Consumables")

        self.front_bar = SkillBarRow(self.skill_choices)
        self.back_bar = SkillBarRow(self.skill_choices)

        self.food = QComboBox()
        self.food.setEditable(True)

        self.potion = QComboBox()
        self.potion.setEditable(True)

        form = QFormLayout()

        form.addRow("Front Bar", self.front_bar)
        form.addRow("Back Bar", self.back_bar)

        consumables = QHBoxLayout()

        consumables.addWidget(QLabel("Food"))
        consumables.addWidget(self.food)
        consumables.addWidget(QLabel("Potion"))
        consumables.addWidget(self.potion)

        form.addRow("Consumables", consumables)

        card.addLayout(form)

        return card

    # --------------------------------------------------
    # Image
    # --------------------------------------------------

    def choose_image(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Character Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )

        if filename:
            self._load_image(filename)

    def clear_image(self):

        self.image_path = ""

        self.image_label.setText("No image")
        self.image_label.setPixmap(QPixmap())

    def _load_image(self, path: str):

        pixmap = QPixmap(path)

        if pixmap.isNull():
            return

        self.image_path = path

        self.image_label.setPixmap(pixmap)
        self.image_label.setText("")

    # --------------------------------------------------
    # Champion points
    # --------------------------------------------------

    def add_cp_row(self, entry: ChampionPointEntry | None = None) -> ChampionPointRow:

        row = ChampionPointRow(self.cp_choices)

        row.removeRequested.connect(self._remove_cp_row)

        if entry is not None:
            row.load(entry)

        self._cp_rows.append(row)

        self.cp_container.addWidget(row)

        return row

    def _remove_cp_row(self, row: ChampionPointRow):

        if row in self._cp_rows:
            self._cp_rows.remove(row)

        row.setParent(None)
        row.deleteLater()

    # --------------------------------------------------
    # Boss alternates
    # --------------------------------------------------

    def add_boss_loadout(self, loadout: BossLoadout | None = None) -> BossLoadoutCard:

        card = BossLoadoutCard(self.skill_choices)

        card.removeRequested.connect(self._remove_boss_loadout)

        if loadout is not None:
            card.load(loadout)

        self._boss_cards.append(card)

        self.boss_container.addWidget(card)

        return card

    def _remove_boss_loadout(self, card: BossLoadoutCard):

        if card in self._boss_cards:
            self._boss_cards.remove(card)

        card.setParent(None)
        card.deleteLater()

    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    @property
    def model(self) -> PlayerBuild:

        armor = {
             slot: row.value.to_dict()
            for slot, row in self.armor_rows.items()
        }

        return PlayerBuild(
            Name=self.name.text().strip(),
            Gamertag=self.gamertag.text().strip(),
            ImagePath=self.image_path,
            Race=self.race.currentText().strip(),
            EsoClass=self.eso_class.currentText(),
            Armor=armor,
            FrontBarWeapon=self.front_bar_weapon.value,
            BackBarWeapon=self.back_bar_weapon.value,
            Necklace=self.necklace.value,
            Ring1=self.ring1.value,
            Ring2=self.ring2.value,
            ChampionPoints=[row.value for row in self._cp_rows],
            FrontBarSkills=self.front_bar.value,
            BackBarSkills=self.back_bar.value,
            Food=self.food.currentText().strip(),
            Potion=self.potion.currentText().strip(),
            Notes=self.notes.toPlainText().strip(),
            BossLoadouts=[card.value for card in self._boss_cards],
        )

    def load(self, model: PlayerBuild):

        self.name.setText(model.Name)
        self.gamertag.setText(model.Gamertag)
        self.race.setCurrentText(model.Race)
        self.eso_class.setCurrentText(model.EsoClass)
        self.notes.setPlainText(model.Notes)

        if model.ImagePath:
            self._load_image(model.ImagePath)
        else:
            self.clear_image()

        # --------------------------------------------------
        # Armor
        # --------------------------------------------------

        for slot, row in self.armor_rows.items():

            entry = model.Armor.get(slot, {})

            row.load(
                GearSlot(
                    Set=entry.get("Set", ""),
                    Trait=entry.get("Trait", ""),
                    Enchant=entry.get("Enchant", ""),
                    Weight=entry.get("Weight", ""),
                )
            )

            # Refresh the compact tile after loading its editor.
            tile = self.gear_tiles.get(slot)

            if tile is not None:
                tile.refresh()

        # --------------------------------------------------
        # Weapons / jewelry
        # --------------------------------------------------

        self.front_bar_weapon.load(model.FrontBarWeapon)
        self.back_bar_weapon.load(model.BackBarWeapon)
        self.necklace.load(model.Necklace)
        self.ring1.load(model.Ring1)
        self.ring2.load(model.Ring2)

        # Refresh those tiles too.
        for slot in (
            "main_hand",
            "off_hand",
            "Neck",
            "Ring1",
            "Ring2",
        ):
            tile = self.gear_tiles.get(slot)

            if tile is not None:
                tile.refresh()

        # --------------------------------------------------
        # Champion Points
        # --------------------------------------------------

        self._clear_cp_rows()

        for entry in model.ChampionPoints:
            self.add_cp_row(entry)

        # --------------------------------------------------
        # Skills
        # --------------------------------------------------

        self.front_bar.load(model.FrontBarSkills)
        self.back_bar.load(model.BackBarSkills)

        # --------------------------------------------------
        # Consumables
        # --------------------------------------------------

        self.food.setCurrentText(model.Food)
        self.potion.setCurrentText(model.Potion)

        # --------------------------------------------------
        # Boss loadouts
        # --------------------------------------------------

        self._clear_boss_loadouts()

        for loadout in model.BossLoadouts:
            self.add_boss_loadout(loadout)

    def clear(self):

        self.load(PlayerBuild())

    def _clear_cp_rows(self):

        for row in list(self._cp_rows):
            self._remove_cp_row(row)

    def _clear_boss_loadouts(self):

        for card in list(self._boss_cards):
            self._remove_boss_loadout(card)
