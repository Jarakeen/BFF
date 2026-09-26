from __future__ import annotations

"""Editable Healer/Tank support-gear idea board for Top Gear."""

from dataclasses import replace
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import DEFAULT_DATABASE
from minmax.gear_set_repository import GearSetRepository
from services.support_gear_reference_service import (
    SupportGearReference,
    SupportGearReferenceService,
)
from ui.components.foundry_card import FoundryCard


class _SupportGearDialog(QDialog):
    def __init__(
        self,
        *,
        role: str,
        reference: SupportGearReference | None = None,
        set_name_choices: tuple[str, ...] = (),
        parent=None,
    ):
        super().__init__(parent)
        self.role = role
        self.reference = reference
        label = "Healer" if role == "healer" else "Tank"
        self.setWindowTitle(f"{'Edit' if reference else 'Add'} {label} Support Set")
        self.setModal(True)
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.set_name = QLineEdit()
        self.set_name.setPlaceholderText("e.g. Pillager's Profit")
        if set_name_choices:
            completer = QCompleter(set_name_choices, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.set_name.setCompleter(completer)
        self.coverage = QLineEdit()
        self.coverage.setPlaceholderText("e.g. Group Ultimate generation")
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("Why / when you would bring it")

        if reference is not None:
            self.set_name.setText(reference.set_name)
            self.coverage.setText(reference.coverage)
            self.notes.setText(reference.notes)

        form.addRow("Set", self.set_name)
        form.addRow("Covers", self.coverage)
        form.addRow("Notes", self.notes)
        root.addLayout(form)

        hint = QLabel(
            "Keep Covers short and raid-facing: Major Slayer, Major Vulnerability, "
            "Armor shred, Ultimate generation, resource sustain, etc."
        )
        hint.setWordWrap(True)
        hint.setProperty("muted", True)
        root.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def result_reference(self) -> SupportGearReference:
        set_name = self.set_name.text().strip()
        coverage = self.coverage.text().strip()
        notes = self.notes.text().strip()
        if not set_name:
            raise ValueError("Set name is required.")
        if not coverage:
            raise ValueError("Coverage / support effect is required.")
        if self.reference is None:
            return SupportGearReference(
                reference_id=str(uuid4()),
                role=self.role,
                set_name=set_name,
                coverage=coverage,
                notes=notes,
                seeded=False,
            )
        return replace(
            self.reference,
            set_name=set_name,
            coverage=coverage,
            notes=notes,
            seeded=False,
        )


class SupportGearReferenceWidget(QWidget):
    def __init__(
        self,
        service: SupportGearReferenceService | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.service = service or SupportGearReferenceService()
        self.set_name_choices = self._load_set_name_choices()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        intro = QLabel(
            "Current support-meta idea board. Keep it practical: what the set covers "
            "and why you might reach for it. This is your editable planning reference, "
            "not a locked ranking."
        )
        intro.setWordWrap(True)
        intro.setProperty("coverageNotesBody", True)
        root.addWidget(intro)

        columns = QHBoxLayout()
        columns.setSpacing(8)

        healer_card, self.healer_table = self._role_card("healer", "Healer Support Sets")
        tank_card, self.tank_table = self._role_card("tank", "Tank Support Sets")
        columns.addWidget(healer_card, 1)
        columns.addWidget(tank_card, 1)
        root.addLayout(columns, 1)

        self.refresh()

    @staticmethod
    def _load_set_name_choices() -> tuple[str, ...]:
        try:
            return tuple(
                sorted(
                    {
                        str(row.name or "").strip()
                        for row in GearSetRepository(DEFAULT_DATABASE).list_sets()
                        if str(row.name or "").strip()
                    },
                    key=str.casefold,
                )
            )
        except Exception:
            return ()

    def _role_card(self, role: str, title: str) -> tuple[FoundryCard, QTableWidget]:
        card = FoundryCard(title, "gear").set_watermark("compass", 0.04)

        actions = QWidget()
        row = QHBoxLayout(actions)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        add = QPushButton("+ Add Set")
        add.setProperty("primary", True)
        add.clicked.connect(lambda *_args, r=role: self._add(r))
        edit = QPushButton("Edit")
        edit.clicked.connect(lambda *_args, r=role: self._edit(r))
        remove = QPushButton("Remove")
        remove.clicked.connect(lambda *_args, r=role: self._remove(r))

        row.addWidget(add)
        row.addWidget(edit)
        row.addWidget(remove)
        card.set_header_action(actions)

        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(("Set", "Covers", "Notes"))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(430)
        table.itemDoubleClicked.connect(lambda *_args, r=role: self._edit(r))
        card.addWidget(table)
        return card, table

    def _table_for(self, role: str) -> QTableWidget:
        return self.healer_table if role == "healer" else self.tank_table

    @staticmethod
    def _selected_reference_id(table: QTableWidget) -> str:
        row = table.currentRow()
        if row < 0:
            return ""
        item = table.item(row, 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _reference_for_selection(self, role: str) -> SupportGearReference | None:
        table = self._table_for(role)
        reference_id = self._selected_reference_id(table)
        if not reference_id:
            return None
        return next(
            (
                row
                for row in self.service.list_for_role(role)
                if row.reference_id == reference_id
            ),
            None,
        )

    def _add(self, role: str) -> None:
        dialog = _SupportGearDialog(
            role=role,
            set_name_choices=self.set_name_choices,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.save(dialog.result_reference())
        except Exception as exc:
            QMessageBox.warning(self, "Could Not Add Set", str(exc))
            return
        self.refresh()

    def _edit(self, role: str) -> None:
        reference = self._reference_for_selection(role)
        if reference is None:
            QMessageBox.information(
                self,
                "Edit Support Set",
                "Select a row first.",
            )
            return
        dialog = _SupportGearDialog(
            role=role,
            reference=reference,
            set_name_choices=self.set_name_choices,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.save(dialog.result_reference())
        except Exception as exc:
            QMessageBox.warning(self, "Could Not Save Set", str(exc))
            return
        self.refresh()

    def _remove(self, role: str) -> None:
        reference = self._reference_for_selection(role)
        if reference is None:
            QMessageBox.information(
                self,
                "Remove Support Set",
                "Select a row first.",
            )
            return
        answer = QMessageBox.question(
            self,
            "Remove Support Set",
            f"Remove {reference.set_name} from the {role.title()} idea board?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.delete(reference.reference_id)
        except Exception as exc:
            QMessageBox.warning(self, "Could Not Remove Set", str(exc))
            return
        self.refresh()

    def refresh(self) -> None:
        for role, table in (
            ("healer", self.healer_table),
            ("tank", self.tank_table),
        ):
            rows = self.service.list_for_role(role)
            table.setRowCount(len(rows))
            for row_index, reference in enumerate(rows):
                values = (
                    reference.set_name,
                    reference.coverage,
                    reference.notes or "—",
                )
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole,
                            reference.reference_id,
                        )
                    item.setToolTip(reference.notes or reference.coverage)
                    table.setItem(row_index, column, item)
            table.resizeColumnsToContents()
            table.horizontalHeader().setStretchLastSection(True)


__all__ = ["SupportGearReferenceWidget"]
