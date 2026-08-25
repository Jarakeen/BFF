from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from services.eso_gear_icons import gear_icon_path


def _configure_search(combo: QComboBox) -> None:
    """Enable case-insensitive substring search without free-form insertion."""
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.NoInsert)
    combo.setDuplicatesEnabled(False)

    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    combo.setCompleter(completer)
    combo.lineEdit().setClearButtonEnabled(True)


class GearSlotTile(QWidget):
    """
    Compact visual representation of one equipment slot.

    The tile displays the equipment slot and current set.
    Clicking it opens a small editor dialog.

    The supplied GearSlotRow remains the source of truth for
    the slot's value, load, and clear behavior.
    """

    changed = Signal()

    def __init__(
        self,
        slot: str,
        label: str,
        editor,
        parent=None,
    ):
        super().__init__(parent)

        self.slot = slot
        self.label = label
        self.editor = editor

        self.setFixedSize(92, 92)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._icon = QLabel()
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setFixedSize(42, 42)

        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._set_name = QLabel()
        self._set_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_name.setWordWrap(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        layout.addWidget(
            self._icon,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

        layout.addWidget(self._label)
        layout.addWidget(self._set_name)

        self._apply_icon()
        self.refresh()

    def _apply_icon(self):
        path = gear_icon_path(self.slot.lower())

        if path and Path(path).exists():
            self._icon.setPixmap(
                QIcon(str(path)).pixmap(QSize(38, 38))
            )
        else:
            self._icon.clear()

    def refresh(self):
        """Refresh the tile from its GearSlotRow."""

        value = self.editor.value

        set_name = value.Set.strip()
        trait = value.Trait.strip()
        enchant = value.Enchant.strip()
        weight = value.Weight.strip()

        details = [
            item
            for item in (
                set_name,
                weight,
                trait,
                enchant,
            )
            if item
        ]

        if details:
            self._set_name.setText(set_name or "Equipped")
            self._set_name.setToolTip("\n".join(details))
        else:
            self._set_name.setText("Empty")
            self._set_name.setToolTip("Empty equipment slot")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_editor()

        super().mousePressEvent(event)

    def _open_editor(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.label)
        dialog.setMinimumWidth(380)

        layout = QVBoxLayout(dialog)

        set_combo = QComboBox()
        set_combo.setEditable(True)
        set_combo.addItem("")

        for i in range(self.editor.set_combo.count()):
            value = self.editor.set_combo.itemText(i)
            if value:
                set_combo.addItem(value)

        set_combo.setCurrentText(
            self.editor.set_combo.currentText()
        )
        _configure_search(set_combo)

        trait_combo = QComboBox()
        for i in range(self.editor.trait_combo.count()):
            trait_combo.addItem(
                self.editor.trait_combo.itemText(i)
            )

        trait_combo.setCurrentText(
            self.editor.trait_combo.currentText()
        )
        _configure_search(trait_combo)

        enchant_combo = QComboBox()
        enchant_combo.setEditable(True)
        enchant_combo.addItem("")

        for i in range(self.editor.enchant_combo.count()):
            value = self.editor.enchant_combo.itemText(i)
            if value:
                enchant_combo.addItem(value)

        enchant_combo.setCurrentText(
            self.editor.enchant_combo.currentText()
        )
        _configure_search(enchant_combo)

        form = QFormLayout()
        form.addRow("Set", set_combo)
        form.addRow("Trait", trait_combo)
        form.addRow("Enchant", enchant_combo)

        weight_combo = None
        if getattr(self.editor, "armor", False):
            weight_combo = QComboBox()

            for i in range(self.editor.weight_combo.count()):
                weight_combo.addItem(
                    self.editor.weight_combo.itemText(i)
                )

            weight_combo.setCurrentText(
                self.editor.weight_combo.currentText()
            )
            _configure_search(weight_combo)
            form.addRow("Weight", weight_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.editor.set_combo.setCurrentText(
                set_combo.currentText().strip()
            )
            self.editor.trait_combo.setCurrentText(
                trait_combo.currentText()
            )
            self.editor.enchant_combo.setCurrentText(
                enchant_combo.currentText().strip()
            )

            if weight_combo is not None:
                self.editor.weight_combo.setCurrentText(
                    weight_combo.currentText()
                )

            self.refresh()
            self.changed.emit()
