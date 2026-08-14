# widgets/build_editor.py
#
# Editable character build for one raid team member:
# identity, image, race/class, gear, CP, skill bars, food
# and potion, plus a scrolling list of boss alternate
# loadouts for the trial. Holds no persistence of its own
# -- the page reads/writes `model` and calls load()/clear(),
# same convention as widgets/roster_record.py.
from widgets.gear_slot_tile import GearSlotTile
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_button import ButtonRole, FoundryButton
from models.roster_model import ESO_CLASSES
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

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
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
    QDialog,
    QDialogButtonBox,
    QSpinBox,
)


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
    """
    ESO combat skill selector.

    Slots 1-5:
        Active combat abilities.

    Slot 6:
        Ultimate abilities.

    Includes:
        - Player abilities
        - Active abilities
        - The selected class's class lines
        - Universal combat skill lines
        - Weapon lines
        - Armor lines
        - World/Guild combat lines
        - Alliance War
        - Vampire / Werewolf

    Excludes:
        - Passive abilities
        - Non-player abilities
        - Crafting/non-combat abilities
        - Other classes' abilities
        - Duplicate rank/morph records
    """

    COMBAT_SKILL_LINES = {
        # Weapon
        "Two Handed",
        "One Hand and Shield",
        "Dual Wield",
        "Bow",
        "Destruction Staff",
        "Restoration Staff",

        # Armor
        "Heavy Armor",
        "Medium Armor",
        "Light Armor",

        # Guild / World
        "Fighters Guild",
        "Mages Guild",
        "Psijic Order",
        "Soul Magic",
        "Undaunted",

        # Alliance War
        "Assault",
        "Support",

        # Special
        "Vampire",
        "Werewolf",
    }

    CLASS_SKILL_LINES = {
        "Dragonknight": {
            "Ardent Flame",
            "Draconic Power",
            "Earthen Heart",
        },

        "Sorcerer": {
            "Dark Magic",
            "Daedric Summoning",
            "Storm Calling",
        },

        "Nightblade": {
            "Assassination",
            "Shadow",
            "Siphoning",
        },

        "Templar": {
            "Aedric Spear",
            "Dawn's Wrath",
            "Restoring Light",
        },

        "Warden": {
            "Animal Companions",
            "Green Balance",
            "Winter's Embrace",
        },

        "Necromancer": {
            "Bone Tyrant",
            "Grave Lord",
            "Living Death",
        },

        "Arcanist": {
            "Herald of the Tome",
            "Soldier of Apocrypha",
            "Curative Runeforms",
        },
    }

    def __init__(
        self,
        skill_choices: list[dict],
        parent=None,
    ):
        super().__init__(parent)

        self.all_skill_choices = skill_choices or []

        self.skill_choices: list[dict] = []

        self.fields: list[QComboBox] = []

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(6)

        for i in range(6):

            field = QComboBox()

            # Skills must come from the database.
            field.setEditable(False)

            field.addItem("")

            if i == 5:
                field.setToolTip("Ultimate")
            else:
                field.setToolTip(
                    f"Skill {i + 1}"
                )

            field.setMinimumSize(
                72,
                72,
            )

            field.setIconSize(
                QSize(56, 56)
            )

            self.fields.append(field)

            layout.addWidget(field)

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def _normalize(value) -> str:

        return " ".join(
            str(value or "")
            .strip()
            .lower()
            .split()
        )

    @staticmethod
    def _as_int(
        value,
        default=0,
    ) -> int:

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return default

    # --------------------------------------------------
    # Combat filtering
    # --------------------------------------------------

    def _is_combat_skill(
        self,
        skill: dict,
    ) -> bool:

        # Must be a player ability.
        if self._as_int(
            skill.get("is_player")
        ) != 1:
            return False

        # Passive abilities do not belong
        # on a skill bar.
        if self._as_int(
            skill.get("is_passive")
        ) != 0:
            return False

        # Must have a name.
        if not str(
            skill.get("name", "")
        ).strip():
            return False

        return True

    # --------------------------------------------------
    # Ultimate detection
    # --------------------------------------------------

    def _is_ultimate(
        self,
        skill: dict,
    ) -> bool:

        return (
            self._as_int(
                skill.get("base_mechanic")
            ) == 8
        )

    # --------------------------------------------------
    # Class / skill-line filtering
    # --------------------------------------------------

    def _class_matches(
        self,
        skill: dict,
        eso_class: str,
    ) -> bool:

        skill_class = str(
            skill.get("class_type", "")
        ).strip()

        skill_line = str(
            skill.get("skill_line", "")
        ).strip()

        selected_class = str(
            eso_class or ""
        ).strip()

        # ----------------------------------------------
        # Class-specific ability
        # ----------------------------------------------

        if skill_class:

            return (
                skill_class
                == selected_class
                and skill_line
                in self.CLASS_SKILL_LINES.get(
                    selected_class,
                    set(),
                )
            )

        # ----------------------------------------------
        # Universal combat ability
        # ----------------------------------------------

        return (
            skill_line
            in self.COMBAT_SKILL_LINES
        )

    # --------------------------------------------------
    # Deduplication
    # --------------------------------------------------

    def _deduplicate(
        self,
        skills: list[dict],
    ) -> list[dict]:

        """
        Collapse duplicate rank/morph records.

        We keep one selectable entry per ability name.
        """

        result: dict[str, dict] = {}

        for skill in skills:

            name = self._normalize(
                skill.get("name")
            )

            if not name:
                continue

            existing = result.get(name)

            if existing is None:

                result[name] = skill

                continue

            # Prefer the higher rank record.
            existing_rank = self._as_int(
                existing.get("rank")
            )

            new_rank = self._as_int(
                skill.get("rank")
            )

            if new_rank > existing_rank:

                result[name] = skill

        return list(
            result.values()
        )

    # --------------------------------------------------
    # Apply class filter
    # --------------------------------------------------

    def set_class(
        self,
        eso_class: str,
    ):

        filtered = []

        for skill in self.all_skill_choices:

            if not isinstance(
                skill,
                dict,
            ):
                continue

            if not self._is_combat_skill(
                skill
            ):
                continue

            if not self._class_matches(
                skill,
                eso_class,
            ):
                continue

            filtered.append(skill)

        self.skill_choices = (
            self._deduplicate(
                filtered
            )
        )

        self._rebuild_combos()

    # --------------------------------------------------
    # Populate controls
    # --------------------------------------------------

    def _rebuild_combos(self):

        current_values = [
            field.currentText().strip()
            for field in self.fields
        ]

        for i, (field, current) in enumerate(
            zip(
                self.fields,
                current_values,
            )
        ):

            field.blockSignals(True)

            field.clear()

            field.addItem("")

            wants_ultimate = (
                i == 5
            )

            for skill in self.skill_choices:

                is_ultimate = (
                    self._is_ultimate(
                        skill
                    )
                )

                if is_ultimate != wants_ultimate:
                    continue

                name = str(
                    skill.get(
                        "name",
                        "",
                    )
                ).strip()

                if not name:
                    continue

                field.addItem(
                    name,
                    skill,
                )

                index = (
                    field.count() - 1
                )

                texture = str(
                    skill.get(
                        "texture",
                        "",
                    ) or ""
                ).strip()

                if texture:

                    field.setItemIcon(
                        index,
                        QIcon(texture),
                    )

            index = field.findText(
                current,
                Qt.MatchFlag.MatchExactly,
            )

            if index >= 0:

                field.setCurrentIndex(
                    index
                )

            else:

                field.setCurrentIndex(0)

            field.blockSignals(False)

    # --------------------------------------------------
    # Values
    # --------------------------------------------------

    @property
    def value(self) -> list[str]:

        return [
            field.currentText().strip()
            for field in self.fields
        ]

    # --------------------------------------------------
    # Load
    # --------------------------------------------------

    def load(
        self,
        skills: list[str],
    ):

        skills = list(
            skills or []
        ) + [""] * 6

        for field, value in zip(
            self.fields,
            skills[:6],
        ):

            value = str(
                value or ""
            ).strip()

            index = field.findText(
                value,
                Qt.MatchFlag.MatchExactly,
            )

            if index >= 0:

                field.setCurrentIndex(
                    index
                )

            else:

                field.setCurrentIndex(0)

    # --------------------------------------------------
    # Clear
    # --------------------------------------------------

    def clear(self):

        for field in self.fields:

            field.setCurrentIndex(0)

class BossLoadoutCard(FoundryCard):
    """One alternate loadout for a specific boss in the trial."""

    removeRequested = Signal(object)

    def __init__(
        self,
        race_choices,
        set_choices,
        skill_choices,
        cp_choices,
        food_choices=None,
        potion_choices=None,
        parent=None,
    ):
        super().__init__(
            "Boss Alternate",
            parent=parent,
        )

        self.skill_choices = skill_choices or []

        self.boss_name = QLineEdit()
        self.boss_name.setPlaceholderText(
            "Boss name"
        )

        self.front_bar = SkillBarRow(
            self.skill_choices
        )

        self.back_bar = SkillBarRow(
            self.skill_choices
        )

        self.food = QComboBox()
        self.potion = QComboBox()

        self.food.addItem("")
        self.food.addItems(food_choices or [])

        self.potion.addItem("")
        self.potion.addItems(potion_choices or [])

        self.notes = QTextEdit()
        self.notes.setPlaceholderText(
            "Positioning, timing, anything that changes for this pull..."
        )
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

        form.addRow(
            "Boss",
            self.boss_name,
        )

        form.addRow(
            "Front Bar",
            self.front_bar,
        )

        form.addRow(
            "Back Bar",
            self.back_bar,
        )

        form.addRow(
            "Food",
            self.food,
        )

        form.addRow(
            "Potion",
            self.potion,
        )

        form.addRow(
            "Notes",
            self.notes,
        )

        self.addLayout(form)

    def set_class(self, eso_class: str):
        self.front_bar.set_class(
            eso_class
        )

        self.back_bar.set_class(
            eso_class
        )

    @property
    def value(self) -> BossLoadout:
        return BossLoadout(
            Boss=self.boss_name.text().strip(),
            FrontBarSkills=self.front_bar.value,
            BackBarSkills=self.back_bar.value,
            Food=self.food.text().strip(),
            Potion=self.potion.text().strip(),
            Notes=self.notes.toPlainText().strip(),
        )

    def load(self, loadout: BossLoadout):
        self.boss_name.setText(
            loadout.Boss or ""
        )

        self.front_bar.load(
            loadout.FrontBarSkills
        )

        self.back_bar.load(
            loadout.BackBarSkills
        )

        self.food.setText(
            loadout.Food or ""
        )

        self.potion.setText(
            loadout.Potion or ""
        )

        self.notes.setPlainText(
            loadout.Notes or ""
        )


class ChampionPointSlot(QFrame):
    """One of the four slottable CP positions in a discipline."""

    clicked = Signal(object)

    def __init__(
        self,
        cp_choices: list[dict],
        discipline_id: int,
        entry: ChampionPointEntry | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.cp_choices = cp_choices
        self.discipline_id = discipline_id
        self.entry = entry or ChampionPointEntry(
            Name="",
            Points="",
        )

        self.setObjectName("ChampionPointSlot")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(2)

        self.icon_label = QLabel("★")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.name_label = QLabel("Empty")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)

        self.points_label = QLabel("")
        self.points_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.points_label)

        self.setMinimumSize(115, 82)
        self.setMaximumWidth(135)

        

        self.refresh()

    def _color(self) -> str:
        return {
            1: "#587A91",
            2: "#9A5C63",
            3: "#5DCC7A",
        }.get(self.discipline_id, "#AAAAAA")

    def refresh(self):

        color = self._color()

        self.icon_label.setStyleSheet(
            f"color: {color}; font-size: 22px;"
        )

        self.name_label.setStyleSheet(
            f"color: {color}; font-weight: 600;"
        )

        name = self.entry.Name.strip()

        if name:
            self.name_label.setText(name)
            self.points_label.setText(
                self.entry.Points.strip()
            )
        else:
            self.name_label.setText("Empty")
            self.points_label.setText("")

        self.setStyleSheet(
            f"""
            QFrame#ChampionPointSlot {{
                border: 1px solid {color};
                border-radius: 6px;
                background: rgba(0, 0, 0, 35);
            }}

            QFrame#ChampionPointSlot:hover {{
                border: 2px solid {color};
            }}
            """
        )

    def set_entry(self, entry: ChampionPointEntry):
        self.entry = entry
        self.refresh()

    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self)

        super().mousePressEvent(event)


class ChampionPointGrid(QWidget):
    """Three ESO CP disciplines with four slottable stars each."""

    DISCIPLINES = (
        (1, "WARFARE"),
        (2, "FITNESS"),
        (3, "CRAFT"),
    )

    changed = Signal()

    def __init__(
        self,
        cp_choices: list[dict],
        parent=None,
    ):
        super().__init__(parent)

        self.cp_choices = cp_choices
        self.slots: list[ChampionPointSlot] = []

        self._build_ui()

    def _build_ui(self):

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        colors = {
            1: "#4DA3FF",
            2: "#FF5C5C",
            3: "#5DCC7A",
        }

        for discipline_id, label in self.DISCIPLINES:

            header = QLabel(label)

            header.setStyleSheet(
                f"""
                QLabel {{
                    color: {colors[discipline_id]};
                    font-weight: 700;
                    font-size: 13px;
                }}
                """
            )

            outer.addWidget(header)

            row = QHBoxLayout()
            row.setSpacing(6)

            for _ in range(4):

                slot = ChampionPointSlot(
                    self.cp_choices,
                    discipline_id,
                )

                slot.clicked.connect(self._edit_slot)

                self.slots.append(slot)
                row.addWidget(slot)

            outer.addLayout(row)

    def _find_cp(self, name: str) -> dict | None:

        name = name.strip()

        if not name:
            return None

        for cp in self.cp_choices:
            if cp.get("name", "").strip() == name:
                return cp

        return None

    @staticmethod
    def _discipline_matches(
        cp: dict,
        discipline_id: int,
    ) -> bool:

        try:
            return int(cp.get("discipline_id")) == discipline_id
        except (TypeError, ValueError):
            return False

    def load_entries(
        self,
        entries: list[ChampionPointEntry],
    ):

        for slot in self.slots:
            slot.set_entry(
                ChampionPointEntry(
                    Name="",
                    Points="",
                )
            )

        for discipline_index, (discipline_id, _) in enumerate(
            self.DISCIPLINES
        ):

            target_slots = self.slots[
                discipline_index * 4:
                discipline_index * 4 + 4
            ]

            matching = []

            for entry in entries:

                cp = self._find_cp(entry.Name)

                if cp is None:
                    continue

                if self._discipline_matches(
                    cp,
                    discipline_id,
                ):
                    matching.append(entry)

            for slot, entry in zip(
                target_slots,
                matching[:4],
            ):
                slot.set_entry(entry)

    def _edit_slot(
        self,
        slot: ChampionPointSlot,
    ):

        cp_choices = [
            cp
            for cp in self.cp_choices
            if self._discipline_matches(
                cp,
                slot.discipline_id,
            )
        ]

        dialog = QDialog(self)
        dialog.setWindowTitle("Champion Point")
        dialog.setMinimumWidth(360)

        layout = QVBoxLayout(dialog)

        combo = QComboBox()
        combo.addItem("")

        for cp in cp_choices:
            combo.addItem(
                cp.get("name", ""),
                cp,
            )

        combo.setCurrentText(slot.entry.Name)

        points = QSpinBox()
        points.setMinimum(0)

        selected = combo.currentData()

        if isinstance(selected, dict):
            try:
                points.setMaximum(
                    int(selected.get("max_points", 100))
                )
            except (TypeError, ValueError):
                points.setMaximum(100)
        else:
            points.setMaximum(100)

        try:
            points.setValue(
                int(slot.entry.Points or 0)
            )
        except (TypeError, ValueError):
            points.setValue(0)

        def update_max():

            cp = combo.currentData()

            if not isinstance(cp, dict):
                points.setMaximum(100)
                return

            try:
                maximum = int(
                    cp.get("max_points", 100)
                )
            except (TypeError, ValueError):
                maximum = 100

            points.setMaximum(maximum)

            if points.value() > maximum:
                points.setValue(maximum)

        combo.currentIndexChanged.connect(update_max)

        form = QFormLayout()
        form.addRow("Champion Point", combo)
        form.addRow("Points", points)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        slot.set_entry(
            ChampionPointEntry(
                Name=combo.currentText().strip(),
                Points=str(points.value()),
            )
        )

        self.changed.emit()

    @property
    def value(self) -> list[ChampionPointEntry]:

        return [
            slot.entry
            for slot in self.slots
            if slot.entry.Name.strip()
        ]
    
class BuildEditor(QWidget):
    """
    Full editable build for one raid team member.

    Meant to sit inside a QScrollArea (the page provides
    that) -- this widget lays everything out vertically and
    does not scroll itself.
    """

    nameChanged = Signal(str)

    def __init__(
        self,
        race_choices: list[str] | None = None,
        set_choices: list[str] | None = None,
        skill_choices: list[dict] | None = None,
        cp_choices: list[dict] | None = None,
        food_choices: list[str] | None = None,
        potion_choices: list[str] | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.race_choices = race_choices or []
        self.set_choices = set_choices or []
        # Keep the complete structured skill records.
        self.skill_choices = skill_choices or []
        self.cp_choices = cp_choices or []
        self.food_choices = food_choices or []
        self.potion_choices = potion_choices or []
        self.image_path = ""

        self._cp_rows: list[ChampionPointSlot] = []
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

        add_boss_button = FoundryButton(
            "+ Add Boss Alternate",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        add_boss_button.clicked.connect(self.add_boss_loadout)

        boss_card_body.addWidget(add_boss_button, 0, Qt.AlignmentFlag.AlignLeft)

        boss_card.addLayout(boss_card_body)

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

        self.eso_class.currentTextChanged.connect(
            self._on_class_changed
)

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

    def _on_class_changed(self, eso_class: str):
        """Refresh available skills when the character class changes."""

        self.front_bar.set_class(
            eso_class
        )

        self.back_bar.set_class(
            eso_class
        )

        for card in self._boss_cards:
            card.set_class(
                eso_class
        )


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
        # LEFT COLUMN
        # --------------------------------------------------
        # Shoulders
        # Hands
        # Ring 1
        # Front Bar
        # --------------------------------------------------

        add_armor_tile(
            "Shoulders",
            "Shoulders",
            0,
            0,
        )

        add_armor_tile(
            "Hands",
            "Hands",
            1,
            0,
        )

        # Ring 1
        self.ring1 = GearSlotRow(
            self.set_choices,
            JEWELRY_TRAITS,
        )

        ring1_tile = GearSlotTile(
            slot="Ring1",
            label="Ring 1",
            editor=self.ring1,
        )

        self.gear_tiles["Ring1"] = ring1_tile

        grid.addWidget(
            ring1_tile,
            2,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

        # Front bar
        self.front_bar_weapon = GearSlotRow(
            self.set_choices,
            WEAPON_TRAITS,
        )

        front_tile = GearSlotTile(
            slot="main_hand",
            label="Front Bar",
            editor=self.front_bar_weapon,
        )

        self.gear_tiles["main_hand"] = front_tile

        grid.addWidget(
            front_tile,
            3,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

        # --------------------------------------------------
        # CENTER COLUMN
        # --------------------------------------------------
        # Helmet
        # Chest
        # Waist
        # Necklace
        # --------------------------------------------------

        add_armor_tile(
            "Head",
            "Helmet",
            0,
            1,
        )

        add_armor_tile(
            "Chest",
            "Chest",
            1,
            1,
        )

        add_armor_tile(
            "Waist",
            "Waist",
            2,
            1,
        )

        self.necklace = GearSlotRow(
            self.set_choices,
            JEWELRY_TRAITS,
        )

        necklace_tile = GearSlotTile(
            slot="Neck",
            label="Necklace",
            editor=self.necklace,
        )

        self.gear_tiles["Neck"] = necklace_tile

        grid.addWidget(
            necklace_tile,
            3,
            1,
            Qt.AlignmentFlag.AlignCenter,
        )

        # --------------------------------------------------
        # RIGHT COLUMN
        # --------------------------------------------------
        # Legs
        # Feet
        # Ring 2
        # Back Bar
        # --------------------------------------------------

        add_armor_tile(
            "Legs",
            "Legs",
            0,
            2,
        )

        add_armor_tile(
            "Feet",
            "Feet",
            1,
            2,
        )

        # Ring 2
        self.ring2 = GearSlotRow(
            self.set_choices,
            JEWELRY_TRAITS,
        )

        ring2_tile = GearSlotTile(
            slot="Ring2",
            label="Ring 2",
            editor=self.ring2,
        )

        self.gear_tiles["Ring2"] = ring2_tile

        grid.addWidget(
            ring2_tile,
            2,
            2,
            Qt.AlignmentFlag.AlignCenter,
        )

        # Back bar
        self.back_bar_weapon = GearSlotRow(
            self.set_choices,
            WEAPON_TRAITS,
        )

        back_tile = GearSlotTile(
            slot="off_hand",
            label="Back Bar",
            editor=self.back_bar_weapon,
        )

        self.gear_tiles["off_hand"] = back_tile

        grid.addWidget(
            back_tile,
            3,
            2,
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

        self.cp_grid = ChampionPointGrid(
            self.cp_choices,
        )

        card.addWidget(self.cp_grid)

        return card

    def _build_skills_card(self) -> FoundryCard:

        card = FoundryCard(
            "Skills & Consumables"
        )

        self.front_bar = SkillBarRow(
            self.skill_choices
        )

        self.back_bar = SkillBarRow(
            self.skill_choices
        )

        # Apply the initial class immediately.
        self._apply_skill_class_filter()

        self.food = QComboBox()
        self.food.setEditable(True)
        self.food.addItem("")
        self.food.addItems(self.food_choices)

        self.potion = QComboBox()
        self.potion.setEditable(True)
        self.potion.addItem("")
        self.potion.addItems(self.potion_choices)

        form = QFormLayout()

        form.addRow(
            "Front Bar",
            self.front_bar
        )

        form.addRow(
            "Back Bar",
            self.back_bar
        )

        consumables = QHBoxLayout()

        consumables.addWidget(
            QLabel("Food")
        )

        consumables.addWidget(
            self.food
        )

        consumables.addWidget(
            QLabel("Potion")
        )

        consumables.addWidget(
            self.potion
        )

        form.addRow(
            "Consumables",
            consumables
        )

        card.addLayout(form)

        return card

    # --------------------------------------------------
    # Image
    # --------------------------------------------------

    def _apply_skill_class_filter(self):

        eso_class = (
            self.eso_class
            .currentText()
            .strip()
        )

        self.front_bar.set_class(
            eso_class
        )

        self.back_bar.set_class(
            eso_class
        )

        for card in self._boss_cards:

            card.set_class(
                eso_class
            )


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
    # Boss alternates
    # --------------------------------------------------

    def add_boss_loadout(
        self,
        loadout: BossLoadout | None = None,
    ) -> BossLoadoutCard:

        card = BossLoadoutCard(
            self.skill_choices
        )

        card.set_class(
            self.eso_class.currentText().strip()
        )

        card.removeRequested.connect(
            self._remove_boss_loadout
        )

        if loadout is not None:
            card.load(loadout)

        self._boss_cards.append(card)

        self.boss_container.addWidget(
            card
        )

        return card

    def _on_class_changed(
        self,
        eso_class: str,
    ):

        self.front_bar.set_class(
            eso_class
        )

        self.back_bar.set_class(
            eso_class
        )

        for card in self._boss_cards:

            card.set_class(
                eso_class
            )

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
            ChampionPoints=self.cp_grid.value,
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
        self.race.setCurrentText(
            model.Race
        )

        self.eso_class.blockSignals(True)

        self.eso_class.setCurrentText(
            model.EsoClass
        )

        self.eso_class.blockSignals(False)

        self._apply_skill_class_filter()

        self.notes.setPlainText(
            model.Notes
        )

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

        self.cp_grid.load_entries(
            model.ChampionPoints
        )
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
