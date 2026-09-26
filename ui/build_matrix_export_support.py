from __future__ import annotations

"""UI for exporting one Saved Build through the Performance Mode Build Matrix."""

import re
from pathlib import Path

from pydantic import ValidationError
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from services.performance_mode_build_matrix_export_service import (
    BuildMatrixExportRequest,
    BuildMatrixIncludeOptions,
    BuildMatrixSlotSelection,
    PerformanceModeBuildMatrixExporter,
    default_export_request,
    variant_choices,
)
from ui.components.foundry_button import ButtonRole, FoundryButton


_SLOT_LABELS = {
    "boss1": "Boss 1",
    "boss2": "Boss 2",
    "boss3": "Boss 3",
    "trash": "Trash / Waves",
    "flex": "Flex / Portal / Special",
}


def _selected_build(page):
    index = int(getattr(page, "selected_index", -1))
    roster = getattr(page, "roster", None)
    members = getattr(roster, "Members", ()) if roster is not None else ()
    if index < 0 or index >= len(members):
        return None
    return members[index]


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "", str(value or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or "performance_mode_build"


class PerformanceModeBuildMatrixExportDialog(QDialog):
    """Strict request builder for one Saved Build export."""

    def __init__(self, build, parent=None) -> None:
        super().__init__(parent)
        self.build = build
        self.setWindowTitle("Export Build to PDF")
        self.setMinimumWidth(640)
        self._default = default_export_request(build)
        self._choices = variant_choices(build)
        self._slot_combos: dict[str, QComboBox] = {}
        self._checks: dict[str, QCheckBox] = {}
        self._mode_group = QButtonGroup(self)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget(scroll)
        root = QVBoxLayout(content)
        root.setSpacing(12)
        root.setContentsMargins(14, 14, 14, 14)

        title = QLabel("Export Build to PDF")
        title.setProperty("heroTitle", True)
        root.addWidget(title)

        intro = QLabel(
            "Create a low-ink, one-page Performance Mode Build Matrix. "
            "The saved Build is the baseline; mapped Context Variants print only their encounter swaps."
        )
        intro.setWordWrap(True)
        intro.setProperty("muted", True)
        root.addWidget(intro)

        template = QGroupBox("Export template")
        template_layout = QFormLayout(template)
        template_value = QLabel("Performance Mode Build Matrix")
        template_value.setStyleSheet("font-weight: 700;")
        template_layout.addRow("Template", template_value)
        root.addWidget(template)

        mode_box = QGroupBox("Export mode")
        mode_layout = QVBoxLayout(mode_box)
        modes = (
            ("current", "Current build only", "Export one matrix page using the current saved Build."),
            (
                "mapped_variants",
                "Current build + mapped variants",
                "Use the saved Build as Boss 1 and map sparse Context Variants into the remaining slots.",
            ),
            (
                "separate_variants",
                "All variants as separate pages",
                "Create a full standalone matrix page for the baseline and each resolved Context Variant.",
            ),
        )
        default_mode = self._default.mode
        for key, label, help_text in modes:
            radio = QRadioButton(label)
            radio.setProperty("modeKey", key)
            radio.setChecked(key == default_mode)
            self._mode_group.addButton(radio)
            mode_layout.addWidget(radio)
            hint = QLabel(help_text)
            hint.setWordWrap(True)
            hint.setProperty("muted", True)
            hint.setContentsMargins(24, 0, 0, 3)
            mode_layout.addWidget(hint)
        self._mode_group.buttonClicked.connect(lambda *_args: self._sync_mapping_enabled())
        root.addWidget(mode_box)

        mapping = QGroupBox("Variant handling")
        mapping_layout = QGridLayout(mapping)
        recommendation = QLabel("Recommended: one baseline, then write only the swaps.")
        recommendation.setWordWrap(True)
        recommendation.setStyleSheet(
            "font-weight: 700; border: 1px solid #C8A46A; border-radius: 5px; padding: 6px;"
        )
        mapping_layout.addWidget(recommendation, 0, 0, 1, 2)

        default_map = {item.slot: item.variant_index for item in self._default.slots}
        for row, slot in enumerate(("boss1", "boss2", "boss3", "trash", "flex"), start=1):
            mapping_layout.addWidget(QLabel(_SLOT_LABELS[slot]), row, 0)
            combo = QComboBox()
            if slot == "boss1":
                combo.addItem("Saved Build baseline", None)
                combo.setEnabled(False)
            else:
                combo.addItem("Leave empty", None)
                for index, label in self._choices:
                    combo.addItem(label, int(index))
                wanted = default_map.get(slot)
                if wanted is not None:
                    found = combo.findData(int(wanted))
                    if found >= 0:
                        combo.setCurrentIndex(found)
            mapping_layout.addWidget(combo, row, 1)
            self._slot_combos[slot] = combo
        root.addWidget(mapping)

        include_box = QGroupBox("Include in export")
        include_layout = QGridLayout(include_box)
        options = (
            ("sets", "Sets"),
            ("weapons", "Weapons"),
            ("skills", "Skills"),
            ("champion_points", "CP"),
            ("notes", "Notes"),
        )
        for index, (key, label) in enumerate(options):
            check = QCheckBox(label)
            check.setChecked(True)
            include_layout.addWidget(check, index // 4, index % 4)
            self._checks[key] = check
        root.addWidget(include_box)

        always_on_note = QLabel(
            "Class Mastery, Food, and Potions are always printed once in the Always On footer. "
            "Race is intentionally omitted from this sheet."
        )
        always_on_note.setWordWrap(True)
        always_on_note.setProperty("muted", True)
        root.addWidget(always_on_note)

        note = QLabel(
            "If the Build has no Context Variants, export produces one filled page. "
            "If variants exist, the canonical context resolver builds each effective setup before differences are printed."
        )
        note.setWordWrap(True)
        note.setProperty("muted", True)
        root.addWidget(note)

        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        self.validation_label.setStyleSheet("color: #B56A4A;")
        root.addWidget(self.validation_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = FoundryButton("Cancel", role=ButtonRole.SECONDARY)
        cancel.clicked.connect(self.reject)
        generate = FoundryButton("Generate PDF", role=ButtonRole.PRIMARY)
        generate.clicked.connect(self._accept_if_valid)
        buttons.addWidget(cancel)
        buttons.addWidget(generate)
        root.addLayout(buttons)
        root.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._sync_mapping_enabled()

    def _mode(self) -> str:
        checked = self._mode_group.checkedButton()
        return str(checked.property("modeKey") if checked is not None else "mapped_variants")

    def _sync_mapping_enabled(self) -> None:
        enabled = self._mode() == "mapped_variants"
        for slot, combo in self._slot_combos.items():
            if slot != "boss1":
                combo.setEnabled(enabled)

    def request(self) -> BuildMatrixExportRequest:
        include = BuildMatrixIncludeOptions(
            sets=bool(self._checks["sets"].isChecked()),
            weapons=bool(self._checks["weapons"].isChecked()),
            skills=bool(self._checks["skills"].isChecked()),
            champion_points=bool(self._checks["champion_points"].isChecked()),
            food=True,
            potions=True,
            class_mastery=True,
            notes=bool(self._checks["notes"].isChecked()),
        )
        slots = tuple(
            BuildMatrixSlotSelection(
                slot=slot,
                variant_index=(
                    int(self._slot_combos[slot].currentData())
                    if self._slot_combos[slot].currentData() is not None
                    else None
                ),
            )
            for slot in ("boss1", "boss2", "boss3", "trash", "flex")
        )
        return BuildMatrixExportRequest(
            mode=self._mode(),
            slots=slots,
            include=include,
        )

    def _accept_if_valid(self) -> None:
        try:
            self.request()
        except (ValidationError, ValueError, TypeError) as exc:
            self.validation_label.setText(f"Export settings are not valid: {exc}")
            return
        self.accept()


def export_selected_build_to_pdf(page) -> None:
    build = _selected_build(page)
    if build is None:
        status = getattr(page, "status", None)
        if status is not None:
            status.warning("Select a saved Build before exporting.")
        return

    dialog = PerformanceModeBuildMatrixExportDialog(build, page)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    try:
        request = dialog.request()
    except (ValidationError, ValueError, TypeError) as exc:
        page.status.error(f"Build Matrix export settings failed validation: {exc}")
        return

    folder = ""
    try:
        folder = page.settings_service.load().get("BuildsExportFolder", "") or ""
    except Exception:
        pass
    stem = _safe_filename(
        " - ".join(
            value
            for value in (
                str(getattr(build, "Name", "") or "").strip(),
                str(getattr(build, "BuildName", "") or "").strip(),
            )
            if value
        )
    )
    start = str(Path(folder) / f"{stem}.pdf") if folder else f"{stem}.pdf"
    filename, _selected_filter = QFileDialog.getSaveFileName(
        page,
        "Export Build to PDF",
        start,
        "PDF (*.pdf)",
    )
    if not filename:
        return

    path = Path(filename)
    if path.suffix.casefold() != ".pdf":
        path = path.with_suffix(".pdf")

    try:
        exporter = PerformanceModeBuildMatrixExporter(
            eso_db_path=Path(page.data_dir) / "eso.db",
        )
        exporter.export_build(build, path, request=request)
        page.status.success(f"Exported Performance Mode Build Matrix to {path}")
    except Exception as exc:
        page.status.error(f"PDF export failed: {exc}")


__all__ = [
    "PerformanceModeBuildMatrixExportDialog",
    "export_selected_build_to_pdf",
]
