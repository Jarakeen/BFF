from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from models.build_model import (
    ARMOR_SLOTS,
    ARMOR_TRAITS,
    WEAPON_TRAITS,
    JEWELRY_TRAITS,
    WEAPON_TYPES,
    BossLoadout,
    ChampionPointEntry,
    GearSlot,
    PlayerBuild,
)
from models.roster_model import ESO_CLASSES
from services.eso_icon_resolver import EsoIconResolver
from services.eso_database import EsoDatabase
from services.reference_data_service import ReferenceDataService
from services.eso_gear_icons import gear_icon_path

QUALITY_CHOICES = ["", "White", "Green", "Blue", "Purple", "Gold"]
LEVEL_CHOICES = ["", "Level 1", "Level 10", "Level 20", "Level 30", "Level 40", "Level 50", "CP10", "CP30", "CP50", "CP70", "CP100", "CP150", "CP160"]
ENCHANT_TIER_CHOICES = ["", "Trifling", "Inferior", "Petty", "Slight", "Minor", "Lesser", "Moderate", "Average", "Strong", "Major", "Greater", "Grand", "Splendid", "Monumental", "Superb", "Truly Superb"]
ENCHANT_CHOICES = ["", "Max Magicka", "Max Health", "Max Stamina", "Prismatic Defense", "Magicka Recovery", "Health Recovery", "Stamina Recovery", "Weapon Damage", "Spell Damage", "Absorb Magicka", "Absorb Health", "Absorb Stamina", "Poison", "Flame", "Frost", "Shock", "Crushing", "Disease", "Bashing", "Decrease Physical Harm"]
MAX_ATTRIBUTE_POINTS = 64


class GearSlotRow(QWidget):
    def __init__(self, set_choices, trait_choices, *, armor=False, weapon=False, parent=None):
        super().__init__(parent)
        self.armor = armor
        self.weapon = weapon
        self.set_combo = self._combo(set_choices, editable=True)
        self.set2_combo = self._combo(set_choices, editable=True)
        self.quality_combo = self._combo(QUALITY_CHOICES)
        self.trait_combo = self._combo(trait_choices)
        type_choices = ["", "Light", "Medium", "Heavy"] if armor else WEAPON_TYPES if weapon else [""]
        self.type_combo = self._combo(type_choices)
        self.type_combo.setEnabled(armor or weapon)
        self.enchant_combo = self._combo(ENCHANT_CHOICES, editable=True)
        self.enchant_tier_combo = self._combo(ENCHANT_TIER_CHOICES)
        self.level_combo = self._combo(LEVEL_CHOICES, editable=True)
        self.quality_combo.currentTextChanged.connect(self._style_quality)
        self._style_quality(self.quality_combo.currentText())

    @staticmethod
    def _combo(values, editable=False):
        combo = QComboBox()
        combo.setMinimumHeight(28)
        combo.setEditable(editable)
        combo.addItems(values)
        combo.setInsertPolicy(QComboBox.NoInsert)
        return combo

    def _style_quality(self, value):
        colors = {"White": "#d8d8d8", "Green": "#5dce72", "Blue": "#4da3ff", "Purple": "#b56cff", "Gold": "#e6b84f"}
        self.quality_combo.setStyleSheet(f"QComboBox {{ border: 1px solid {colors.get(value, '#6b6255')}; }}")

    @property
    def value(self):
        return GearSlot(
            Set=self.set_combo.currentText().strip(),
            Set2=self.set2_combo.currentText().strip(),
            Quality=self.quality_combo.currentText().strip(),
            Trait=self.trait_combo.currentText().strip(),
            Enchant=self.enchant_combo.currentText().strip(),
            EnchantTier=self.enchant_tier_combo.currentText().strip(),
            Level=self.level_combo.currentText().strip(),
            Weight=self.type_combo.currentText().strip() if self.armor else "",
            WeaponType=self.type_combo.currentText().strip() if self.weapon else "",
        )

    def load(self, slot):
        self.set_combo.setCurrentText(slot.Set or "")
        self.set2_combo.setCurrentText(getattr(slot, "Set2", "") or "")
        self.quality_combo.setCurrentText(getattr(slot, "Quality", "") or "")
        self.trait_combo.setCurrentText(slot.Trait or "")
        self.enchant_combo.setCurrentText(slot.Enchant or "")
        self.enchant_tier_combo.setCurrentText(getattr(slot, "EnchantTier", "") or "")
        self.level_combo.setCurrentText(getattr(slot, "Level", "") or "")
        if self.armor:
            self.type_combo.setCurrentText(getattr(slot, "Weight", "") or "")
        elif self.weapon:
            self.type_combo.setCurrentText(getattr(slot, "WeaponType", "") or "")
        else:
            self.type_combo.setCurrentIndex(0)

    def clear(self):
        self.load(GearSlot())


class SkillBarRow(QWidget):
    def __init__(self, skill_choices, parent=None):
        super().__init__(parent); self.all_skill_choices = skill_choices or []; self.skill_choices = list(self.all_skill_choices); self.fields = []; self.icon_resolver = EsoIconResolver(); layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(6)
        for index in range(6):
            combo = QComboBox(); combo.setEditable(True); combo.setInsertPolicy(QComboBox.NoInsert); combo.setMinimumHeight(38); combo.setIconSize(QSize(26, 26)); combo.setToolTip("Ultimate" if index == 5 else f"Skill {index + 1}"); self.fields.append(combo); layout.addWidget(combo, 1)
    @staticmethod
    def _skill_dicts(skills): return [s for s in skills if isinstance(s, dict) and str(s.get("name", "")).strip()]
    def set_class(self, eso_class):
        skills = self._skill_dicts(self.all_skill_choices)
        if not skills: self.skill_choices = list(self.all_skill_choices); self._rebuild(); return
        universal = {"Two Handed", "One Hand and Shield", "Dual Wield", "Bow", "Destruction Staff", "Restoration Staff", "Heavy Armor", "Medium Armor", "Light Armor", "Fighters Guild", "Mages Guild", "Psijic Order", "Soul Magic", "Undaunted", "Assault", "Support", "Vampire", "Werewolf"}; class_lines = {"Dragonknight": {"Ardent Flame", "Draconic Power", "Earthen Heart"}, "Sorcerer": {"Dark Magic", "Daedric Summoning", "Storm Calling"}, "Nightblade": {"Assassination", "Shadow", "Siphoning"}, "Templar": {"Aedric Spear", "Dawn's Wrath", "Restoring Light"}, "Warden": {"Animal Companions", "Green Balance", "Winter's Embrace"}, "Necromancer": {"Bone Tyrant", "Grave Lord", "Living Death"}, "Arcanist": {"Herald of the Tome", "Soldier of Apocrypha", "Curative Runeforms"}}; filtered = []
        for skill in skills:
            if int(skill.get("is_player") or 0) != 1 or int(skill.get("is_passive") or 0) != 0: continue
            line = str(skill.get("skill_line") or "").strip(); owner = str(skill.get("class_type") or "").strip()
            if owner:
                if owner == eso_class and line in class_lines.get(eso_class, set()): filtered.append(skill)
            elif line in universal: filtered.append(skill)
        seen = {}
        for skill in filtered:
            key = str(skill.get("name", "")).strip().casefold()
            if key and key not in seen: seen[key] = skill
        self.skill_choices = list(seen.values()); self._rebuild()
    def _rebuild(self):
        current = [field.currentText().strip() for field in self.fields]; structured = self._skill_dicts(self.skill_choices); names = [str(s.get("name", "")).strip() for s in structured] if structured else [str(s).strip() for s in self.skill_choices]
        for i, combo in enumerate(self.fields):
            combo.blockSignals(True); combo.clear(); combo.addItem(""); wants_ultimate = i == 5
            if structured:
                for skill in structured:
                    if (int(skill.get("base_mechanic") or 0) == 8) != wants_ultimate: continue
                    name = str(skill.get("name", "")).strip(); combo.addItem(name, skill); texture = str(skill.get("texture") or "").strip(); path = self.icon_resolver.resolve(texture)
                    if path: combo.setItemIcon(combo.count() - 1, QIcon(str(path)))
            else:
                for name in names: combo.addItem(name)
            if current[i]: combo.setCurrentIndex(combo.findText(current[i], Qt.MatchExactly) if combo.findText(current[i], Qt.MatchExactly) >= 0 else 0)
            combo.blockSignals(False)
    @property
    def value(self): return [field.currentText().strip() for field in self.fields]
    def load(self, skills):
        values = list(skills or []) + [""] * 6
        for field, value in zip(self.fields, values[:6]): field.setCurrentIndex(field.findText(str(value or ""), Qt.MatchExactly) if field.findText(str(value or ""), Qt.MatchExactly) >= 0 else 0)
    def clear(self):
        for field in self.fields: field.setCurrentIndex(0)


class CompactCPSlot(QWidget):
    changed = Signal()
    def __init__(self, choices, discipline_id, entry=None, parent=None):
        super().__init__(parent); self.choices = choices; self.discipline_id = discipline_id; self.entry = entry or ChampionPointEntry(); self.combo = QComboBox(); self.combo.setEditable(True); self.combo.setInsertPolicy(QComboBox.NoInsert); self.points = QSpinBox(); self.points.setRange(0, 100); self.points.setFixedWidth(54); minus = FoundryButton("−", role=ButtonRole.GHOST, compact=True); plus = FoundryButton("+", role=ButtonRole.GHOST, compact=True); minus.setFixedWidth(28); plus.setFixedWidth(28); row = QHBoxLayout(self); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(4); row.addWidget(self.combo, 1); row.addWidget(self.points); row.addWidget(minus); row.addWidget(plus); minus.clicked.connect(lambda: self.points.setValue(max(0, self.points.value() - 1))); plus.clicked.connect(lambda: self.points.setValue(min(100, self.points.value() + 1))); self.combo.currentTextChanged.connect(lambda *_: self._sync()); self.points.valueChanged.connect(lambda *_: self._sync()); self._populate()
    def _populate(self):
        self.combo.blockSignals(True); self.combo.clear(); self.combo.addItem("")
        for cp in self.choices:
            if isinstance(cp, dict):
                try: matches = int(cp.get("discipline_id") or 0) == self.discipline_id
                except (TypeError, ValueError): matches = False
                if matches: self.combo.addItem(str(cp.get("name", "")), cp)
            else: self.combo.addItem(str(cp))
        self.combo.setCurrentText(self.entry.Name)
        try: self.points.setValue(int(self.entry.Points or 0))
        except (TypeError, ValueError): self.points.setValue(0)
        self.combo.blockSignals(False)
    def _sync(self): self.entry = ChampionPointEntry(Name=self.combo.currentText().strip(), Points=str(self.points.value())); self.changed.emit()
    def load(self, entry): self.entry = entry; self._populate()
    def clear(self): self.load(ChampionPointEntry())
    @property
    def value(self): return self.entry


class ChampionPointGrid(QWidget):
    changed = Signal()
    DISCIPLINES = ((3, "THE THIEF", "#5DCC7A"), (1, "THE MAGE", "#4DA3FF"), (2, "THE WARRIOR", "#FF5C5C"))
    def __init__(self, cp_choices, parent=None):
        super().__init__(parent); self.cp_choices = cp_choices or []; self.slots = []; outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(4)
        for discipline_id, label, color in self.DISCIPLINES:
            row = QHBoxLayout(); row.setSpacing(8); heading = QLabel(f"✧  {label}"); heading.setFixedWidth(145); heading.setStyleSheet(f"color:{color}; font-weight:700;"); row.addWidget(heading)
            for _ in range(4):
                slot = CompactCPSlot(self.cp_choices, discipline_id); slot.changed.connect(self.changed.emit); self.slots.append(slot); row.addWidget(slot, 1)
            outer.addLayout(row)
    def load_entries(self, entries):
        for slot in self.slots: slot.clear()
        for entry in entries or []:
            if not entry.Name.strip(): continue
            for slot in self.slots:
                if slot.entry.Name: continue
                if any(isinstance(cp, dict) and str(cp.get("name", "")).strip() == entry.Name.strip() and int(cp.get("discipline_id") or 0) == slot.discipline_id for cp in self.cp_choices): slot.load(entry); break
    @property
    def value(self): return [slot.value for slot in self.slots if slot.value.Name.strip()]


class BossLoadoutCard(FoundryCard):
    removeRequested = Signal(object)
    def __init__(self, skill_choices, parent=None):
        super().__init__("Boss Alternate", parent=parent); self.boss_name = QLineEdit(); self.front_bar = SkillBarRow(skill_choices); self.back_bar = SkillBarRow(skill_choices); self.food = QLineEdit(); self.potion = QLineEdit(); self.notes = QLineEdit(); remove = FoundryButton("Remove", role=ButtonRole.DANGER, compact=True); remove.clicked.connect(lambda: self.removeRequested.emit(self)); self.set_header_action(remove); form = QFormLayout(); form.addRow("Boss", self.boss_name); form.addRow("Front Bar", self.front_bar); form.addRow("Back Bar", self.back_bar); form.addRow("Food", self.food); form.addRow("Potion", self.potion); form.addRow("Notes", self.notes); self.addLayout(form)
    def set_class(self, eso_class): self.front_bar.set_class(eso_class); self.back_bar.set_class(eso_class)
    @property
    def value(self): return BossLoadout(BossName=self.boss_name.text().strip(), FrontBarSkills=self.front_bar.value, BackBarSkills=self.back_bar.value, Food=self.food.text().strip(), Potion=self.potion.text().strip(), Notes=self.notes.text().strip())
    def load(self, loadout): self.boss_name.setText(loadout.BossName); self.front_bar.load(loadout.FrontBarSkills); self.back_bar.load(loadout.BackBarSkills); self.food.setText(loadout.Food); self.potion.setText(loadout.Potion); self.notes.setText(loadout.Notes)


class BuildEditor(QWidget):
    nameChanged = Signal(str); saveRequested = Signal(); cancelRequested = Signal(); addBuildRequested = Signal()
    def __init__(self, race_choices=None, set_choices=None, skill_choices=None, cp_choices=None, food_choices=None, potion_choices=None, parent=None):
        super().__init__(parent); self.race_choices = race_choices or []; self.set_choices = set_choices or []; self.skill_choices = skill_choices or []; self.cp_choices = cp_choices or []; self.food_choices = food_choices or []; self.potion_choices = potion_choices or []; self.image_path = ""; self._notes = ""; self._boss_cards = []; self._hydrate_reference_data(); self._build_ui()
    def showEvent(self, event):
        super().showEvent(event); parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, QDialog): parent.resize(max(parent.width(), 1600), max(parent.height(), 920)); break
            parent = parent.parentWidget()
    def _hydrate_reference_data(self):
        db_path = Path(__file__).resolve().parents[1] / "data" / "eso.db"
        try:
            db = EsoDatabase(db_path); ref = ReferenceDataService(db)
            if not self.skill_choices or all(isinstance(x, str) for x in self.skill_choices): self.skill_choices = ref.list_skills()
            if not self.cp_choices or all(isinstance(x, str) for x in self.cp_choices): self.cp_choices = ref.list_champion_points()
            if not self.food_choices: self.food_choices = ref.list_food_names()
            if not self.potion_choices: self.potion_choices = ref.list_potion_names()
        except Exception: pass
    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(8); root.addWidget(self._build_identity_card()); root.addWidget(self._build_gear_card()); root.addWidget(self._build_cp_card()); root.addWidget(self._build_skills_card()); root.addWidget(self._build_boss_card())
    @staticmethod
    def _line(placeholder=""):
        widget = QLineEdit(); widget.setPlaceholderText(placeholder); widget.setMinimumHeight(28); return widget
    @staticmethod
    def _combo(values, editable=False):
        widget = QComboBox(); widget.setEditable(editable); widget.setInsertPolicy(QComboBox.NoInsert); widget.addItems(values); widget.setMinimumHeight(28); return widget
    @staticmethod
    def _attribute_spin():
        spin = QSpinBox(); spin.setRange(0, MAX_ATTRIBUTE_POINTS); spin.setFixedWidth(70); spin.setMinimumHeight(28); return spin
    def _update_attribute_limits(self):
        values = (self.attribute_health.value(), self.attribute_magicka.value(), self.attribute_stamina.value()); total = sum(values)
        for spin, value in zip((self.attribute_health, self.attribute_magicka, self.attribute_stamina), values): spin.setMaximum(min(MAX_ATTRIBUTE_POINTS, MAX_ATTRIBUTE_POINTS - (total - value)))
        self.attribute_total.setText(str(total))
    def _build_identity_card(self):
        card = FoundryCard("Identity"); grid = QGridLayout(); grid.setContentsMargins(8, 6, 8, 6); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(6)
        fields = [("Character Name", self._line("Character name")), ("@Gamertag", self._line("@Gamertag")), ("Race", self._combo(self.race_choices, True)), ("Class", self._combo(ESO_CLASSES)), ("Role", self._combo(["", "Tank", "Healer", "DD"])), ("Alliance", self._combo(["", "Aldmeri Dominion", "Daggerfall Covenant", "Ebonheart Pact"]))]
        self.name, self.gamertag, self.race, self.eso_class, self.role, self.alliance = [w for _, w in fields]; self.name.textChanged.connect(self.nameChanged.emit); self.eso_class.currentTextChanged.connect(self._apply_class)
        for column, (label, widget) in enumerate(fields): grid.addWidget(QLabel(label), 0, column); grid.addWidget(widget, 1, column)
        self.vampire = QCheckBox("Vampire"); self.werewolf = QCheckBox("Werewolf"); self.attribute_health = self._attribute_spin(); self.attribute_magicka = self._attribute_spin(); self.attribute_stamina = self._attribute_spin(); self.attribute_total = QLabel("0"); self.attribute_total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); self.attribute_total.setProperty("overviewStatValue", True)
        grid.addWidget(self.vampire, 2, 0); grid.addWidget(self.werewolf, 2, 1)
        for column, label, spin in ((2, "Health", self.attribute_health), (3, "Magicka", self.attribute_magicka), (4, "Stamina", self.attribute_stamina)): grid.addWidget(QLabel(label), 2, column); grid.addWidget(spin, 3, column)
        grid.addWidget(QLabel("Total / 64"), 2, 5); grid.addWidget(self.attribute_total, 3, 5)
        self.vampire.toggled.connect(self._sync_affiliations); self.werewolf.toggled.connect(self._sync_affiliations)
        for spin in (self.attribute_health, self.attribute_magicka, self.attribute_stamina): spin.valueChanged.connect(self._update_attribute_limits)
        card.addLayout(grid); return card
    def _sync_affiliations(self):
        if self.vampire.isChecked() and self.werewolf.isChecked():
            sender = self.sender(); other = self.werewolf if sender is self.vampire else self.vampire; other.blockSignals(True); other.setChecked(False); other.blockSignals(False)
    def _gear_icon(self, slot):
        path = gear_icon_path(slot.lower()); label = QLabel(); label.setFixedSize(22, 22); label.setAlignment(Qt.AlignCenter)
        if path and Path(path).exists(): label.setPixmap(QIcon(str(path)).pixmap(QSize(18, 18)))
        return label
    def _build_gear_card(self):
        card = FoundryCard("Gear"); grid = QGridLayout(); grid.setContentsMargins(8, 5, 8, 5); grid.setHorizontalSpacing(6); grid.setVerticalSpacing(3); headers = ["", "Slot", "Set 1", "Set 2 (Monster/Backup)", "Quality", "Trait", "Weight / Weapon", "Enchantment", "Enchant Tier", "Level", ""]
        for column, text in enumerate(headers): header = QLabel(text); header.setStyleSheet("font-weight:700;"); grid.addWidget(header, 0, column)
        self.gear_rows = {}; specs = [("Head", "Head", True), ("Shoulders", "Shoulders", True), ("Chest", "Chest", True), ("Hands", "Hands", True), ("Waist", "Waist", True), ("Legs", "Legs", True), ("Feet", "Feet", True), ("Neck", "Neck", False), ("Ring1", "Ring 1", False), ("Ring2", "Ring 2", False), ("main_hand", "Front Bar", False), ("off_hand", "Back Bar", False)]
        for row, (slot, label, armor) in enumerate(specs, 1):
            grid.addWidget(self._gear_icon(slot), row, 0); slot_label = QLabel(label); slot_label.setMinimumWidth(78); grid.addWidget(slot_label, row, 1); traits = ARMOR_TRAITS if armor else JEWELRY_TRAITS if slot in {"Neck", "Ring1", "Ring2"} else WEAPON_TRAITS; weapon = slot in {"main_hand", "off_hand"}; editor = GearSlotRow(self.set_choices, traits, armor=armor, weapon=weapon); self.gear_rows[slot] = editor
            for column, widget in enumerate([editor.set_combo, editor.set2_combo, editor.quality_combo, editor.trait_combo, editor.type_combo, editor.enchant_combo, editor.enchant_tier_combo, editor.level_combo], 2): grid.addWidget(widget, row, column)
            remove = FoundryButton("×", role=ButtonRole.GHOST, compact=True); remove.setFixedWidth(28); remove.clicked.connect(editor.clear); grid.addWidget(remove, row, 10)
        card.addLayout(grid); return card
    def _build_cp_card(self): card = FoundryCard("Champion Points"); self.cp_grid = ChampionPointGrid(self.cp_choices); card.addWidget(self.cp_grid); return card
    def _build_skills_card(self):
        card = FoundryCard("Skills & Consumables"); self.front_bar = SkillBarRow(self.skill_choices); self.back_bar = SkillBarRow(self.skill_choices); self._apply_class(); form = QFormLayout(); form.addRow("Front Bar", self.front_bar); form.addRow("Back Bar", self.back_bar); self.food = self._combo(self.food_choices, True); self.potion = self._combo(self.potion_choices, True); consumables = QHBoxLayout(); consumables.addWidget(QLabel("Food")); consumables.addWidget(self.food, 1); consumables.addWidget(QLabel("Potion")); consumables.addWidget(self.potion, 1); form.addRow("Consumables", consumables); card.addLayout(form); return card
    def _build_boss_card(self):
        card = FoundryCard("Boss Alternates"); body = QVBoxLayout(); self.boss_container = QVBoxLayout(); body.addLayout(self.boss_container); actions = QHBoxLayout(); actions.setSpacing(8); add_boss = FoundryButton("+ Add Boss Alternate", role=ButtonRole.SECONDARY, compact=True); add_build = FoundryButton("+ Add New Build", role=ButtonRole.SECONDARY, compact=True); save = FoundryButton("Save This Build", role=ButtonRole.PRIMARY, compact=True); cancel = FoundryButton("Cancel", role=ButtonRole.SECONDARY, compact=True); add_boss.clicked.connect(self.add_boss_loadout); add_build.clicked.connect(self._handle_add_build); save.clicked.connect(self.saveRequested.emit); cancel.clicked.connect(self.cancelRequested.emit); actions.addWidget(add_boss); actions.addStretch(); actions.addWidget(add_build); actions.addWidget(save); actions.addWidget(cancel); body.addLayout(actions); card.addLayout(body); return card
    def _apply_class(self, _class_name=None):
        if not hasattr(self, "front_bar"): return
        eso_class = self.eso_class.currentText().strip(); self.front_bar.set_class(eso_class); self.back_bar.set_class(eso_class)
        for card in self._boss_cards: card.set_class(eso_class)
    def add_boss_loadout(self, loadout=None):
        card = BossLoadoutCard(self.skill_choices); card.set_class(self.eso_class.currentText().strip()); card.removeRequested.connect(self._remove_boss_loadout); self._boss_cards.append(card); self.boss_container.addWidget(card)
        if loadout: card.load(loadout)
        return card
    def _remove_boss_loadout(self, card):
        if card in self._boss_cards: self._boss_cards.remove(card)
        card.setParent(None); card.deleteLater()
    def _handle_add_build(self):
        page = self; dialog = None
        while page is not None:
            if isinstance(page, QDialog): dialog = page
            if hasattr(page, "roster") and hasattr(page, "_save") and hasattr(page, "_refresh_roster"): break
            page = page.parentWidget()
        if page is None or not hasattr(page, "roster"): self.addBuildRequested.emit(); return
        if len(page.roster.Members) >= 12: return
        page.roster.Members.append(PlayerBuild()); page.selected_index = len(page.roster.Members) - 1; page._save(); page._refresh_roster()
        if dialog is not None: dialog.reject()
    @property
    def model(self):
        armor = {slot: row.value.to_dict() for slot, row in self.gear_rows.items() if slot in ARMOR_SLOTS}
        return PlayerBuild(Name=self.name.text().strip(), Gamertag=self.gamertag.text().strip(), ImagePath=self.image_path, Race=self.race.currentText().strip(), EsoClass=self.eso_class.currentText().strip(), Role=self.role.currentText().strip(), Alliance=self.alliance.currentText().strip(), Vampire=self.vampire.isChecked(), Werewolf=self.werewolf.isChecked(), AttributeHealth=self.attribute_health.value(), AttributeMagicka=self.attribute_magicka.value(), AttributeStamina=self.attribute_stamina.value(), Armor=armor, FrontBarWeapon=self.gear_rows["main_hand"].value, BackBarWeapon=self.gear_rows["off_hand"].value, Necklace=self.gear_rows["Neck"].value, Ring1=self.gear_rows["Ring1"].value, Ring2=self.gear_rows["Ring2"].value, ChampionPoints=self.cp_grid.value, FrontBarSkills=self.front_bar.value, BackBarSkills=self.back_bar.value, Food=self.food.currentText().strip(), Potion=self.potion.currentText().strip(), Notes=self._notes, BossLoadouts=[card.value for card in self._boss_cards])
    def load(self, model):
        self.image_path = model.ImagePath; self._notes = model.Notes; self.name.setText(model.Name); self.gamertag.setText(model.Gamertag); self.race.setCurrentText(model.Race); self.eso_class.setCurrentText(model.EsoClass); self.role.setCurrentText(getattr(model, "Role", "") or ""); self.alliance.setCurrentText(getattr(model, "Alliance", "") or "")
        self.vampire.blockSignals(True); self.werewolf.blockSignals(True); self.attribute_health.blockSignals(True); self.attribute_magicka.blockSignals(True); self.attribute_stamina.blockSignals(True); self.vampire.setChecked(bool(getattr(model, "Vampire", False))); self.werewolf.setChecked(bool(getattr(model, "Werewolf", False)) and not self.vampire.isChecked()); self.attribute_health.setValue(max(0, min(MAX_ATTRIBUTE_POINTS, int(getattr(model, "AttributeHealth", 0) or 0)))); self.attribute_magicka.setValue(max(0, min(MAX_ATTRIBUTE_POINTS, int(getattr(model, "AttributeMagicka", 0) or 0)))); self.attribute_stamina.setValue(max(0, min(MAX_ATTRIBUTE_POINTS, int(getattr(model, "AttributeStamina", 0) or 0)))); self.attribute_stamina.blockSignals(False); self.attribute_magicka.blockSignals(False); self.attribute_health.blockSignals(False); self.werewolf.blockSignals(False); self.vampire.blockSignals(False); self._sync_affiliations(); self._update_attribute_limits(); self._apply_class()
        for slot, row in self.gear_rows.items():
            if slot in ARMOR_SLOTS: row.load(GearSlot.from_dict(model.Armor.get(slot, {})))
            else: row.load({"main_hand": model.FrontBarWeapon, "off_hand": model.BackBarWeapon, "Neck": model.Necklace, "Ring1": model.Ring1, "Ring2": model.Ring2}[slot])
        self.cp_grid.load_entries(model.ChampionPoints); self.front_bar.load(model.FrontBarSkills); self.back_bar.load(model.BackBarSkills); self.food.setCurrentText(model.Food); self.potion.setCurrentText(model.Potion)
        for card in list(self._boss_cards): self._remove_boss_loadout(card)
        for loadout in model.BossLoadouts: self.add_boss_loadout(loadout)
    def choose_image(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Character Image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if filename: self.image_path = filename
