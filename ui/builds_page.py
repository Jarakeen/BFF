from __future__ import annotations

from collections import Counter
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from models.build_model import BuildRoster, PlayerBuild
from models.roster_model import RosterMember
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.reference_data_service import ReferenceDataService
from services.roster_service import RosterService
from services.settings_service import SettingsService
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from widgets.build_editor import BuildEditor


class BuildsPage(FoundryPage):
    """Builds Desk presentation layer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_dir = get_data_dir()
        self.database = EsoDatabase(self.data_dir / "eso.db")
        self.reference = ReferenceDataService(self.database)
        self.roster_service = RosterService(self.database)
        self.build_service = BuildService(self.data_dir / "builds.json")
        self.settings_service = SettingsService(Path("settings.json"))
        self.roster = BuildRoster()
        self.roster_members: list[RosterMember] = []
        self.selected_index = 0
        self._build_ui()
        self._load()

    def _build_ui(self):
        self.header = FoundryHeader(title="Builds", subtitle="Maintain equipment. Support the expedition.", department="Raid Operations")
        self.set_header(self.header)
        self.trial_combo = QComboBox()
        self.trial_combo.setMinimumWidth(230)
        self.trial_combo.addItems(self._list_trials())
        self.trial_combo.currentTextChanged.connect(self._refresh_detail)
        self.view_combo = QComboBox()
        self.view_combo.addItems(["Current Raid", "All Builds"])
        self.view_combo.currentTextChanged.connect(self._refresh_roster)
        self.header.add_context_widget(self._context_field("TRIAL", self.trial_combo))
        self.header.add_context_widget(self._context_field("VIEW", self.view_combo))
        actions = QWidget()
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.addStretch()
        self.edit_button = FoundryButton("Edit Build", role=ButtonRole.SECONDARY)
        self.save_button = FoundryButton("Save Builds", role=ButtonRole.SUCCESS)
        self.export_button = FoundryButton("Export Builds", role=ButtonRole.SECONDARY)
        self.edit_button.clicked.connect(self._edit_selected)
        self.save_button.clicked.connect(self._save)
        self.export_button.clicked.connect(self._export_csv)
        action_layout.addWidget(self.edit_button)
        action_layout.addWidget(self.save_button)
        action_layout.addWidget(self.export_button)
        self.set_actions(actions)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.roster_list = QListWidget()
        self.roster_list.setMinimumWidth(230)
        self.roster_list.setMaximumWidth(320)
        self.roster_list.currentRowChanged.connect(self._select_member)
        self.splitter.addWidget(self._roster_card())
        self.detail = QWidget()
        self.detail_layout = QVBoxLayout(self.detail)
        self.detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_layout.setSpacing(10)
        self.splitter.addWidget(self.detail)
        self.splitter.setStretchFactor(1, 1)
        self.add_workspace(self.splitter)
        self.status = FoundryStatusBar()
        self.set_status(self.status)

    def _context_field(self, title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def _roster_card(self) -> QWidget:
        card = FoundryCard("Team Roster")
        card.setMinimumWidth(230)
        card.addWidget(self.roster_list)
        return card

    def _list_trials(self) -> list[str]:
        try:
            rows = self.database.execute("SELECT DISTINCT content_name FROM bosses WHERE content_name IS NOT NULL AND TRIM(content_name) != '' ORDER BY content_name COLLATE NOCASE").fetchall()
            trials = [row["content_name"] for row in rows]
            return trials or ["Current Raid"]
        except Exception:
            return ["Current Raid"]

    def _load(self):
        try:
            self.roster = self.build_service.load()
        except Exception as exc:
            self.roster = BuildRoster()
            self.status.error(f"Failed to load builds: {exc}")
        try:
            self.roster_members = self.roster_service.list_members()
        except Exception:
            self.roster_members = []
        self._refresh_roster()
        self.status.info(f"{len(self.roster.Members)} build(s) loaded.")

    def _refresh_roster(self, *_args):
        current = self.selected_index
        self.roster_list.blockSignals(True)
        self.roster_list.clear()
        for index, build in enumerate(self.roster.Members):
            role, status = self._role_for(build)
            name = build.Name.strip() or build.Gamertag.strip() or f"Member {index + 1}"
            label = f"{name}   {role}" if role else name
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setToolTip(f"{build.EsoClass or 'Class not set'} • {status}")
            self.roster_list.addItem(item)
        if self.roster_list.count():
            self.roster_list.setCurrentRow(min(max(current, 0), self.roster_list.count() - 1))
        self.roster_list.blockSignals(False)
        self._select_member(self.roster_list.currentRow())

    def _role_for(self, build: PlayerBuild) -> tuple[str, str]:
        target = (build.Name or build.Gamertag).strip().casefold()
        for member in self.roster_members:
            if target in {(member.CharacterName or "").strip().casefold(), (member.PlayerName or "").strip().casefold()}:
                return member.PrimaryRole, member.Status
        return "", "Active"

    def _select_member(self, row: int):
        if row < 0 or row >= len(self.roster.Members):
            return
        self.selected_index = row
        self._refresh_detail()

    def _clear_detail(self):
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                BuildsPage._clear_layout(child_layout)

    def _refresh_detail(self, *_args):
        self._clear_detail()
        if not self.roster.Members:
            return
        build = self.roster.Members[self.selected_index]
        role, _ = self._role_for(build)
        name = build.Name.strip() or build.Gamertag.strip() or "Unnamed Member"
        self.detail_layout.addWidget(self._identity_header(name, role, build))
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(self._gear_card(build), 3)
        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(self._status_card(build))
        right.addWidget(self._set_bonus_card(build))
        top.addLayout(right, 2)
        self.detail_layout.addLayout(top)

        lower = QHBoxLayout()
        lower.setSpacing(10)
        cp_card = self._cp_card(build)
        skills_card = self._skills_card(build)
        notes_card = self._notes_card(build)
        cp_card.setMinimumWidth(170)
        cp_card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        skills_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        notes_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        lower.addWidget(cp_card, 1)
        lower.addWidget(skills_card, 3)
        lower.addWidget(notes_card, 1)
        self.detail_layout.addLayout(lower)

        self.detail_layout.addWidget(self._scribed_skills_card(build))
        self.detail_layout.addWidget(self._alternates_card(build))
        self.detail_layout.addStretch(1)

    def _identity_header(self, name: str, role: str, build: PlayerBuild) -> QWidget:
        frame = QFrame()
        frame.setProperty("foundryCard", True)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        badge = QLabel("◆")
        badge.setProperty("cardIcon", True)
        layout.addWidget(badge)
        text = QVBoxLayout()
        title = QLabel(name.upper())
        title.setProperty("pageTitle", True)
        text.addWidget(title)
        parts = [p for p in [role, build.EsoClass, build.Race] if p]
        subtitle = QLabel("  •  ".join(parts) or "Build not configured")
        subtitle.setProperty("pageSubtitle", True)
        text.addWidget(subtitle)
        layout.addLayout(text, 1)
        cp = QLabel(f"CP {self._cp_total(build)}")
        cp.setProperty("cardBadge", True)
        layout.addWidget(cp)
        return frame

    def _gear_card(self, build: PlayerBuild) -> QWidget:
        card = FoundryCard("Gear")
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Slot", "Set", "Trait", "Enchant", "Status"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setMinimumHeight(330)
        table.horizontalHeader().setStretchLastSection(True)
        rows = list(build.Armor.items()) + [("Neck", build.Necklace), ("Ring 1", build.Ring1), ("Ring 2", build.Ring2), ("Main Hand", build.FrontBarWeapon), ("Off Hand", build.BackBarWeapon)]
        for slot, value in rows:
            if hasattr(value, "Set"):
                set_name, trait, enchant = value.Set, value.Trait, value.Enchant
            else:
                set_name, trait, enchant = value.get("Set", ""), value.get("Trait", ""), value.get("Enchant", "")
            row = table.rowCount()
            table.insertRow(row)
            status = "✓ Complete" if set_name and trait else ("⚠ Partial" if set_name else "Missing")
            for col, text in enumerate([slot, set_name or "—", trait or "—", enchant or "—", status]):
                table.setItem(row, col, QTableWidgetItem(str(text)))
        card.addWidget(table)
        return card

    def _status_card(self, build: PlayerBuild) -> QWidget:
        card = FoundryCard("Build Status")
        for label, value in self._status_rows(build):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addStretch()
            row.addWidget(QLabel(value))
            card.addLayout(row)
        return card

    def _status_rows(self, build: PlayerBuild) -> list[tuple[str, str]]:
        gear = self._all_gear(build)
        gear_total = 12
        gear_complete = sum(1 for slot in gear if self._gear_filled(slot))
        traits = sum(1 for slot in gear if self._gear_trait(slot))
        skills = sum(1 for skill in (build.FrontBarSkills + build.BackBarSkills) if str(skill).strip())
        cp = len([entry for entry in build.ChampionPoints if entry.Name.strip()])
        readiness = round(((gear_complete / gear_total) + (traits / gear_total) + (skills / 12) + (1 if cp else 0)) / 4 * 100)
        return [("Readiness", f"{readiness}%"), ("Gear Complete", f"{gear_complete}/{gear_total}"), ("Traits", f"{traits}/{gear_total}"), ("Champion Points", "Configured" if cp else "Missing"), ("Skills", f"{skills}/12")]

    def _set_bonus_card(self, build: PlayerBuild) -> QWidget:
        card = FoundryCard("Set Bonuses")
        counts = Counter()
        for slot in self._all_gear(build):
            name = slot.Set.strip() if hasattr(slot, "Set") else str(slot.get("Set", "")).strip()
            if name:
                counts[name] += 1
        if not counts:
            card.addWidget(QLabel("No equipped sets recorded."))
        else:
            for name, count in counts.most_common():
                row = QHBoxLayout()
                row.addWidget(QLabel(name))
                row.addStretch()
                row.addWidget(QLabel(f"{count}/5"))
                card.addLayout(row)
        return card

    def _cp_card(self, build: PlayerBuild) -> QWidget:
        card = FoundryCard("CP & Stats Snapshot (all Champion Passives included)")
        entries = [entry for entry in build.ChampionPoints if entry.Name.strip()]
        if not entries:
            label = QLabel("Champion Points not configured.")
            label.setWordWrap(True)
            card.addWidget(label)
        else:
            for entry in entries:
                text = entry.Name.strip()
                if entry.Points.strip():
                    text += f"  {entry.Points.strip()}"
                label = QLabel(text)
                label.setWordWrap(True)
                card.addWidget(label)
        return card

    def _skills_card(self, build: PlayerBuild) -> QWidget:
        card = FoundryCard("Skills & Consumables")
        front = [s for s in build.FrontBarSkills if s.strip()]
        back = [s for s in build.BackBarSkills if s.strip()]
        card.addWidget(QLabel("Front Bar"))
        front_label = QLabel("  •  ".join(front) or "Not configured")
        front_label.setWordWrap(True)
        front_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        card.addWidget(front_label)
        card.addWidget(QLabel("Back Bar"))
        back_label = QLabel("  •  ".join(back) or "Not configured")
        back_label.setWordWrap(True)
        back_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        card.addWidget(back_label)
        food = QLabel(f"Food: {build.Food or '—'}")
        potion = QLabel(f"Potion: {build.Potion or '—'}")
        food.setWordWrap(True)
        potion.setWordWrap(True)
        card.addWidget(food)
        card.addWidget(potion)
        return card

    def _notes_card(self, build: PlayerBuild) -> QWidget:
        card = FoundryCard("Notes")
        label = QLabel(build.Notes.strip() or "No build notes recorded.")
        label.setWordWrap(True)
        card.addWidget(label)
        return card

    def _scribed_skill_names(self) -> list[str]:
        names: set[str] = set()
        try:
            for skill in self.reference.list_skills():
                if not isinstance(skill, dict):
                    continue
                try:
                    crafted = int(skill.get("is_crafted") or 0) == 1
                except (TypeError, ValueError):
                    crafted = False
                name = str(skill.get("name") or "").strip()
                if crafted and name:
                    names.add(name)
        except Exception:
            return []
        return sorted(names, key=str.casefold)

    def _scribed_skills_card(self, build: PlayerBuild) -> QWidget:
        card = FoundryCard("Scribed Skills")
        selected = [str(name).strip() for name in getattr(build, "ScribedSkills", []) if str(name).strip()]
        if selected:
            label = QLabel("  •  ".join(selected))
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            card.addWidget(label)
        else:
            label = QLabel("No scribed skill access recorded for this build.")
            label.setWordWrap(True)
            card.addWidget(label)
        actions = QHBoxLayout()
        actions.addStretch()
        edit = FoundryButton("Choose Scribed Skills", role=ButtonRole.SECONDARY, compact=True)
        edit.clicked.connect(self._edit_scribed_skills)
        actions.addWidget(edit)
        card.addLayout(actions)
        return card

    def _edit_scribed_skills(self):
        if not self.roster.Members or self.selected_index >= len(self.roster.Members):
            return
        build = self.roster.Members[self.selected_index]
        available = self._scribed_skill_names()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Scribed Skills — {build.Name or build.BuildName or 'Build'}")
        dialog.resize(520, 620)
        layout = QVBoxLayout(dialog)
        explanation = QLabel("Choose the scribed skills this character has access to. Selected skills become eligible for this build's skill bars.")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        choices = QListWidget()
        selected = {str(name).strip().casefold() for name in getattr(build, "ScribedSkills", []) if str(name).strip()}
        for name in available:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name.casefold() in selected else Qt.CheckState.Unchecked)
            choices.addItem(item)
        layout.addWidget(choices, 1)
        actions = QHBoxLayout()
        actions.addStretch()
        cancel = FoundryButton("Cancel", role=ButtonRole.SECONDARY, compact=True)
        save = FoundryButton("Save Scribed Access", role=ButtonRole.PRIMARY, compact=True)
        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(dialog.accept)
        actions.addWidget(cancel)
        actions.addWidget(save)
        layout.addLayout(actions)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        build.ScribedSkills = [
            choices.item(index).text().strip()
            for index in range(choices.count())
            if choices.item(index).checkState() == Qt.CheckState.Checked
        ]
        self._save()
        self._refresh_detail()

    def _alternates_card(self, build: PlayerBuild) -> QWidget:
        card = FoundryCard("Boss Alternates")
        if not build.BossLoadouts:
            card.addWidget(QLabel("No boss-specific alternate loadouts."))
            return card
        for loadout in build.BossLoadouts:
            name = loadout.BossName.strip() or "Unnamed Boss"
            notes = f" — {loadout.Notes.strip()}" if loadout.Notes.strip() else ""
            card.addWidget(QLabel(f"{name}{notes}"))
        return card

    @staticmethod
    def _all_gear(build: PlayerBuild) -> list:
        return list(build.Armor.values()) + [build.Necklace, build.Ring1, build.Ring2, build.FrontBarWeapon, build.BackBarWeapon]

    @staticmethod
    def _gear_filled(slot) -> bool:
        if hasattr(slot, "Set"):
            return bool(slot.Set.strip())
        return bool(str(slot.get("Set", "")).strip())

    @staticmethod
    def _gear_trait(slot) -> bool:
        if hasattr(slot, "Trait"):
            return bool(slot.Trait.strip())
        return bool(str(slot.get("Trait", "")).strip())

    @staticmethod
    def _cp_total(build: PlayerBuild) -> str:
        total = 0
        for entry in build.ChampionPoints:
            try:
                total += int(entry.Points)
            except (TypeError, ValueError):
                continue
        return str(total) if total else "—"

    def _editor(self, build: PlayerBuild | None = None) -> BuildEditor:
        skills = self.reference.list_skills()
        skill_choices = [
            skill
            for skill in skills
            if isinstance(skill, dict) and str(skill.get("name", "")).strip()
        ]
        cp = self.reference.list_champion_points()
        cp_choices = [point for point in cp if isinstance(point, dict) and str(point.get("name", "")).strip()]
        editor = BuildEditor(
            race_choices=self.reference.list_race_names(),
            set_choices=self.reference.list_gear_set_names(),
            skill_choices=skill_choices,
            cp_choices=cp_choices,
        )
        # GearSlotRow is a controller object whose child fields are inserted into
        # BuildEditor's visible grid. Keep the controller parented and hidden so
        # Qt cannot surface it as a stray top-level/floating form widget.
        for row in getattr(editor, "gear_rows", {}).values():
            row.setParent(editor)
            row.hide()
        return editor

    def _edit_selected(self):
        if not self.roster.Members:
            return
        build = self.roster.Members[self.selected_index]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Build — {build.Name or 'Unnamed Member'}")
        dialog.setMinimumSize(1200, 760)
        dialog.resize(1500, 920)
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        editor = self._editor(build)
        scroll.setWidget(editor)
        layout.addWidget(scroll, 1)
        editor.load(build)
        editor.saveRequested.connect(dialog.accept)
        editor.cancelRequested.connect(dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated = editor.model
            existing_scribed = [
                str(name).strip()
                for name in getattr(build, "ScribedSkills", [])
                if str(name).strip()
            ]
            canonical_scribed = {
                name.casefold(): name
                for name in self._scribed_skill_names()
            }
            slotted_names = list(updated.FrontBarSkills) + list(updated.BackBarSkills)
            for loadout in updated.BossLoadouts:
                slotted_names.extend(loadout.FrontBarSkills)
                slotted_names.extend(loadout.BackBarSkills)
            used_scribed = [
                canonical_scribed[str(name).strip().casefold()]
                for name in slotted_names
                if str(name).strip().casefold() in canonical_scribed
            ]
            updated.ScribedSkills = list(dict.fromkeys(existing_scribed + used_scribed))
            self.roster.Members[self.selected_index] = updated
            self._save()
            self._refresh_roster()

    def _save(self):
        abs_path = self.build_service.builds_path.resolve()
        try:
            self.build_service.save(self.roster)
        except Exception as exc:
            self.status.error(f"Save failed writing {abs_path}: {exc}")
            return
        try:
            reloaded = self.build_service.load()
        except Exception as exc:
            self.status.error(f"Saved to {abs_path}, but re-reading it back failed: {exc}")
            return
        if reloaded != self.roster:
            self.status.error(f"Save to {abs_path} did not verify: reloaded data does not match what was saved.")
            return
        self.status.success(f"Builds saved to {abs_path}.")

    def _export_csv(self):
        folder = ""
        try:
            folder = self.settings_service.load().get("BuildsExportFolder", "") or ""
        except Exception:
            pass
        filename, _ = QFileDialog.getSaveFileName(self, "Export Builds as CSV", str(Path(folder) / "raid_builds.csv") if folder else "raid_builds.csv", "CSV Files (*.csv)")
        if not filename:
            return
        try:
            self.build_service.export_csv(self.roster, Path(filename))
            self.status.success(f"Exported builds to {filename}")
        except Exception as exc:
            self.status.error(f"Export failed: {exc}")