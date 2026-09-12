from __future__ import annotations

"""Builds-page intake for ESO Armory + Character screenshots.

Real Xbox Armory captures show that one loadout is spread across multiple
subviews: equipment/attributes, skills, and Champion Points.  The import dialog
therefore accepts a set of Armory screenshots plus one matching Character sheet
and stages them together for review-first recognition.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.build_screenshot_import_service import BuildScreenshotImportService
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard

_INSTALLED = False


class _ScreenshotPicker(QWidget):
    def __init__(self, title: str, hint: str, parent=None):
        super().__init__(parent)
        self._path = Path()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        heading = QLabel(title)
        heading.setProperty("sidebarHeading", True)
        root.addWidget(heading)

        subtitle = QLabel(hint)
        subtitle.setWordWrap(True)
        subtitle.setProperty("muted", True)
        root.addWidget(subtitle)

        row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("No screenshot selected")
        browse = QPushButton("Choose…")
        browse.clicked.connect(self._choose)
        row.addWidget(self.path_edit, 1)
        row.addWidget(browse)
        root.addLayout(row)

        self.preview = QLabel("Screenshot preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(180)
        self.preview.setProperty("foundryCard", True)
        root.addWidget(self.preview)

    @property
    def path(self) -> Path:
        return self._path

    def _choose(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose ESO Screenshot",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if filename:
            self.set_path(Path(filename))

    def set_path(self, path: Path) -> None:
        self._path = Path(path)
        self.path_edit.setText(str(self._path))
        self._show_preview(self._path)

    def _show_preview(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.preview.setText("Preview unavailable")
            self.preview.setPixmap(QPixmap())
            return
        self.preview.setText("")
        self.preview.setPixmap(
            pixmap.scaled(
                520,
                260,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class _ArmoryScreenshotPicker(QWidget):
    """Select several Armory subviews belonging to one saved build."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paths: list[Path] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        heading = QLabel("ARMORY SCREENSHOTS")
        heading.setProperty("sidebarHeading", True)
        root.addWidget(heading)

        subtitle = QLabel(
            "Select every useful Armory view for this build. Equipment/attributes, Skills, "
            "and Champion are separate screens on Xbox, so BFF keeps them as one evidence set."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("muted", True)
        root.addWidget(subtitle)

        row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("No Armory screenshots selected")
        browse = QPushButton("Choose Screens…")
        browse.clicked.connect(self._choose)
        row.addWidget(self.path_edit, 1)
        row.addWidget(browse)
        root.addLayout(row)

        self.preview = QLabel("Armory screenshot preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(180)
        self.preview.setProperty("foundryCard", True)
        root.addWidget(self.preview)

        self.selection_note = QLabel(
            "Recommended: equipment/attributes + skills + Champion. Add more if another Armory view contains useful build data."
        )
        self.selection_note.setWordWrap(True)
        self.selection_note.setProperty("muted", True)
        root.addWidget(self.selection_note)

    @property
    def paths(self) -> list[Path]:
        return list(self._paths)

    def _choose(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose ESO Armory Screenshots",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if filenames:
            self.set_paths([Path(filename) for filename in filenames])

    def set_paths(self, paths: list[Path]) -> None:
        self._paths = [Path(path) for path in paths]
        if not self._paths:
            self.path_edit.clear()
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Armory screenshot preview")
            self.selection_note.setText("No Armory screenshots selected.")
            return

        names = ", ".join(path.name for path in self._paths[:3])
        if len(self._paths) > 3:
            names += f" + {len(self._paths) - 3} more"
        self.path_edit.setText(names)
        self.selection_note.setText(
            f"{len(self._paths)} Armory screenshot(s) selected • first image shown above"
        )

        pixmap = QPixmap(str(self._paths[0]))
        if pixmap.isNull():
            self.preview.setText("Preview unavailable")
            self.preview.setPixmap(QPixmap())
            return
        self.preview.setText("")
        self.preview.setPixmap(
            pixmap.scaled(
                520,
                260,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class BuildScreenshotImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Build from ESO Screenshots")
        self.resize(1080, 720)
        self.service = BuildScreenshotImportService(get_data_dir() / "build_imports")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        body = QWidget(scroll)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(4, 4, 4, 4)
        body_layout.setSpacing(10)

        title = QLabel("SCREENSHOT BUILD IMPORT")
        title.setProperty("pageTitle", True)
        body_layout.addWidget(title)

        intro = QLabel(
            "Capture one character's Armory views plus the main Character sheet. BFF keeps the "
            "screens together so recognition can combine loadout, skills, CP, attributes, and "
            "character identity without making you type every toon by hand."
        )
        intro.setWordWrap(True)
        intro.setProperty("pageSubtitle", True)
        body_layout.addWidget(intro)

        capture_card = FoundryCard("Recommended Capture Set")
        capture_text = QLabel(
            "1. Armory equipment/attributes view: build name, gear, weapons, jewelry, Mundus, attributes.\n"
            "2. Armory Skills view: both skill bars and ultimates.\n"
            "3. Armory Champion view: the slotted CP stars for all three disciplines.\n"
            "4. Character Sheet → Description: character name, race, class, alliance and stable identity details.\n"
            "Extra Armory screenshots are welcome when one screen cannot show the whole list."
        )
        capture_text.setWordWrap(True)
        capture_card.addWidget(capture_text)
        body_layout.addWidget(capture_card)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        self.armory = _ArmoryScreenshotPicker()
        self.character = _ScreenshotPicker(
            "CHARACTER SCREENSHOT",
            "Use Character Sheet → Description when possible. It exposes the stable character identity that the Armory build itself does not.",
        )
        grid.addWidget(self.armory, 0, 0)
        grid.addWidget(self.character, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        body_layout.addLayout(grid)

        status = QLabel(
            "Recognition will create a reviewable draft before anything is allowed into builds.json. Missing or ambiguous fields stay unresolved instead of being guessed."
        )
        status.setWordWrap(True)
        status.setProperty("muted", True)
        body_layout.addWidget(status)
        body_layout.addStretch(1)

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.stage_button = FoundryButton("📷 Add Screenshot Set", role=ButtonRole.SUCCESS)
        self.stage_button.clicked.connect(self._stage)
        actions.addWidget(cancel)
        actions.addWidget(self.stage_button)
        root.addLayout(actions)

    def _stage(self) -> None:
        if not self.armory.paths or not self.character.path:
            QMessageBox.warning(
                self,
                "Screenshots needed",
                "Choose at least one Armory screenshot and the matching Character screenshot first.",
            )
            return
        try:
            intake = self.service.stage(
                armory_images=self.armory.paths,
                character_image=self.character.path,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Screenshot import failed", str(exc))
            return

        QMessageBox.information(
            self,
            "Screenshots added",
            "The screenshot set is safely staged for build analysis.\n\n"
            f"Import ID: {intake.intake_id}\n"
            f"Armory screens: {len(intake.armory_images)}\n\n"
            "Nothing was written into your saved builds yet. The analyzer will create a review draft first.",
        )
        self.accept()


def _open_screenshot_import(page) -> None:
    dialog = BuildScreenshotImportDialog(page)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        pending = dialog.service.pending()
        page.status.success(
            f"Screenshot set staged • {len(pending)} build import(s) waiting for analysis."
        )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    original_build_ui = BuildsPage._build_ui

    def build_ui_with_screenshot_import(self):
        original_build_ui(self)
        button = FoundryButton(
            "📷 Import Screenshots",
            role=ButtonRole.SECONDARY,
            compact=True,
        )
        button.setToolTip(
            "Stage several ESO Armory views plus the matching Character sheet for build import."
        )
        button.clicked.connect(lambda _checked=False, page=self: _open_screenshot_import(page))
        self.import_screenshots_button = button

        actions = getattr(self, "actions", None)
        layout = actions.layout() if actions is not None else None
        if layout is not None:
            insert_at = 1 if layout.count() > 1 else 0
            layout.insertWidget(insert_at, button)
        else:
            self.header.add_context_widget(button)

    BuildsPage._build_ui = build_ui_with_screenshot_import
    _INSTALLED = True
