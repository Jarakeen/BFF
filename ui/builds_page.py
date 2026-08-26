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
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

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
        self.data_dir = Path(__file__).resolve().parents[1] / "data"
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
        self.header = FoundryHeader(
            title="Builds",
            subtitle="Maintain equipment. Support the expedition.",
            department="Raid Operations",
        )
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
            rows = self.database.execute("""
                SELECT DISTINCT content_name
                FROM bosses
                WHERE content_name IS NOT NULL
                  AND TRIM(content_name) != ''
                ORDER BY content_name COLLATE NOCASE
            """).fetchall()
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
            row = min(max(current, 0), self.roster_list.count() - 1)
            self.roster_list.setCurrentRow(row)
        self.roster_list.blockSignals(False)
        self._select_member(self.roster_list.currentRow())

    def _role_for(self, build: PlayerBuild) -> tuple[str, str]:
        target = (build.Name or build.Gamertag).strip().casefold()
        for member in self.roster_members:
            if target in {
                (member.CharacterName or "").strip().casefold(),
                (member.PlayerName or "").strip().casefold(),
            }:
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
            if widget is not None:
                widget.deleteLater()

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
        lower.addWidget(self._cp_card(build), 1)
        lower.addWidget(self._skills_card(build), 1)
        lower.addWidget(self._notes_card(build), 1)
        self.detail_layout.addLayout(lower)
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
        rows: list[tuple[str, object]] = []
        for slot, value in build.Armor.items():
            rows.append((slot, value))
        rows.extend([
            ("Neck", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
            ("Main Hand", build.FrontBarWeapon),
            ("Off Hand", build.BackBarWeapon),
        ])
        for slot, value in rows:
            if hasattr(value, "Set"):
                set_name, trait, enchant = value.Set, value.Trait, value.Enchant
            else:
                set_name = value.get("Set", "")
                trait = value.get("Trait", "")
                enchant = value.get("Enchant", "")
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
        gear_total = 12
        gear_complete = sum(1 for slot in self._all_gear(build) if self._gear_filled(slot))
        traits = sum(1 for slot in self._all_gear(build) if self._gear_trait(slot))
        skills = sum(1 for skill in (build.FrontBarSkills + build.BackBarSkills) if str(skill).strip())
        cp = len([entry for entry in build.ChampionPoints if entry.Name.strip()])
        readiness = round(((gear_complete / gear_total) + (traits / gear_total) + (skills / 12) + (1 if cp else 0)) / 4 * 100)
        return [
            ("Readiness", f"{readiness}%"),
            ("Gear Complete", f"{gear_complete}/{gear_total}"),
            ("Traits", f"{traits}/{gear_total}"),
            ("Champion Points", "Configured" if cp else "Missing"),
            ("Skills", f"{skills}/12"),
        ]

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
        card = FoundryCard("CP & Stats Snapshot")
        entries = [entry for entry in build.ChampionPoints if entry.Name.strip()]
        if not entries:
            card.addWidget(QLabel("Champion Points not configured."))
        else:
            for entry in entries:
                text = entry.Name.strip()
                if entry.Points.strip():
                    text += f"  {entry.Points.strip()}"
                card.addWidget(QLabel(text))
        return card

    def _skills_card(self, build: PlayerBuild) -> QWidget:
        card = FoundryCard("Skills & Consumables")
        front = [s for s in build.FrontBarSkills if s.strip()]
        back = [s for s in build.BackBarSkills if s.strip()]
        card.addWidget(QLabel("Front Bar"))
        card.addWidget(QLabel("  •  ".join(front) or "Not configured"))
        card.addWidget(QLabel("Back Bar"))
        card.addWidget(QLabel("  •  ".join(back) or "Not configured"))
        card.addWidget(QLabel(f"Food: {build.Food or '—'}"))
        card.addWidget(QLabel(f"Potion: {build.Potion or '—'}"))
        return card

    def _notes_card(self, build: PlayerBuild) -> QWidget:
        card = FoundryCard("Notes")
        card.addWidget(QLabel(build.Notes.strip() or "No build notes recorded."))
        return card

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
        return list(build.Armor.values()) + [
            build.Necklace,
            build.Ring1,
            build.Ring2,
            build.FrontBarWeapon,
            build.BackBarWeapon,
        ]

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

    def _editor(self) -> BuildEditor:
        skills = self.reference.list_skills()

        skill_choices = list(dict.fromkeys(
            skill["name"]
            for skill in skills
            if isinstance(skill, dict) and skill.get("name")
        ))

        cp = self.reference.list_champion_points()

        cp_choices = list(dict.fromkeys(
            point["name"]
            for point in cp
            if isinstance(point, dict) and point.get("name")
        ))

        return BuildEditor(
            race_choices=self.reference.list_race_names(),
            set_choices=self.reference.list_gear_set_names(),
            skill_choices=skill_choices,
            cp_choices=cp_choices,
        )

    def _edit_selected(self):
        if not self.roster.Members:
            return

        build = self.roster.Members[self.selected_index]
        editor = self._editor()
        editor.load(build)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Build — {build.Name or 'Unnamed Member'}")
        dialog.resize(1200, 850)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(editor)
        layout.addWidget(scroll, 1)

        # Save This Build / Cancel live inside the editor itself (next
        # to + Add Boss Alternate), not in a separate dialog button box
        # that could scroll out of view on a tall editor.
        editor.saveRequested.connect(dialog.accept)
        editor.cancelRequested.connect(dialog.reject)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.roster.Members[self.selected_index] = editor.model
            self._save()
            self._refresh_roster()

    def _save(self):
        """
        Save, then immediately read the same file back through
        the same BuildService and compare it against what's in
        memory. "No exception" is not proof the data is on
        disk -- this is. Success is only reported once the
        round trip actually matches.
        """
        abs_path = self.build_service.builds_path.resolve()

        try:
            self.build_service.save(self.roster)
        except Exception as exc:
            self.status.error(
                f"Save failed writing {abs_path}: {exc}"
            )
            return

        try:
            reloaded = self.build_service.load()
        except Exception as exc:
            self.status.error(
                f"Saved to {abs_path}, but re-reading it back "
                f"failed: {exc}"
            )
            return

        if reloaded != self.roster:
            mismatch = self._describe_roster_mismatch(reloaded, self.roster)
            self.status.error(
                f"Save to {abs_path} did not verify: reloaded data "
                f"does not match what was saved ({mismatch})."
            )
            return

        self.status.success(f"Builds saved to {abs_path}.")

    @staticmethod
    def _describe_roster_mismatch(
        reloaded: BuildRoster, expected: BuildRoster
    ) -> str:
        """
        Best-effort diagnostic string for a failed save/reload
        round trip, so an error report is actionable instead of
        just "it didn't match".
        """
        if len(reloaded.Members) != len(expected.Members):
            return (
                f"expected {len(expected.Members)} member(s), "
                f"found {len(reloaded.Members)} on reload"
            )

        for index, (got, want) in enumerate(
            zip(reloaded.Members, expected.Members)
        ):
            if got != want:
                name = want.Name or want.Gamertag or f"member {index + 1}"
                fields = [
                    field
                    for field in want.__dataclass_fields__
                    if getattr(got, field) != getattr(want, field)
                ]
                return f"{name}: field(s) differ after reload: {', '.join(fields)}"

        return "mismatch detected"

    def _export_csv(self):
        folder = ""
        try:
            folder = self.settings_service.load().get("BuildsExportFolder", "") or ""
        except Exception:
            pass

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Builds as CSV",
            str(Path(folder) / "raid_builds.csv") if folder else "raid_builds.csv",
            "CSV Files (*.csv)",
        )
        if not filename:
            return
        try:
            self.build_service.export_csv(self.roster, Path(filename))
            self.status.success(f"Exported builds to {filename}")
        except Exception as exc:
            self.status.error(f"Export failed: {exc}")