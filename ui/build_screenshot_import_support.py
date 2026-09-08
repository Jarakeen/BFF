from __future__ import annotations

"""Builds-page intake for ESO Armory + Character screenshots.

This is intentionally a review-first intake surface.  The image recognition
layer will be tuned against real ESO screenshots rather than guessing at screen
geometry before we have examples.  Captures are copied into data/build_imports
with a manifest so they are ready for later analysis without making the user
re-capture every character.
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
        if not filename:
            return
        self.set_path(Path(filename))

    def set_path(self, path: Path) -> None:
        self._path = Path(path)
        self.path_edit.setText(str(self._path))
        pixmap = QPixmap(str(self._path))
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
        self.resize(1040, 690)
        self.service = BuildScreenshotImportService(get_data_dir() / "build_imports")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("SCREENSHOT BUILD IMPORT")
        title.setProperty("pageTitle", True)
        root.addWidget(title)

        intro = QLabel(
            "Capture the same character in the Armory and on the main Character page. "
            "BFF keeps the pair together so the build analyzer can combine loadout evidence "
            "with character identity/stats instead of making you type every toon by hand."
        )
        intro.setWordWrap(True)
        intro.setProperty("pageSubtitle", True)
        root.addWidget(intro)

        capture_card = FoundryCard("Recommended Capture Pair")
        capture_card.addWidget(QLabel(
            "1. Armory page: capture the loadout/build view as completely as possible.\n"
            "2. Character page: capture character name, class/race/stats and equipped information that is visible.\n"
            "You can crop out unrelated desktop clutter, but keep the ESO UI itself intact."
        ))
        root.addWidget(capture_card)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        self.armory = _ScreenshotPicker(
            "ARMORY SCREENSHOT",
            "Primary evidence for the saved loadout, skills, equipment, and build identity.",
        )
        self.character = _ScreenshotPicker(
            "CHARACTER SCREENSHOT",
            "Companion evidence for character identity and whatever stats/equipment the screen exposes.",
        )
        grid.addWidget(self.armory, 0, 0)
        grid.addWidget(self.character, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        root.addLayout(grid, 1)

        status = QLabel(
            "Current stage: capture intake. Recognition will create a reviewable draft before anything is allowed into builds.json."
        )
        status.setWordWrap(True)
        status.setProperty("muted", True)
        root.addWidget(status)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.stage_button = FoundryButton("📷 Add Screenshot Pair", role=ButtonRole.SUCCESS)
        self.stage_button.clicked.connect(self._stage)
        actions.addWidget(cancel)
        actions.addWidget(self.stage_button)
        root.addLayout(actions)

    def _stage(self) -> None:
        if not self.armory.path or not self.character.path:
            QMessageBox.warning(
                self,
                "Two screenshots needed",
                "Choose both the Armory screenshot and the main Character screenshot first.",
            )
            return
        try:
            intake = self.service.stage(
                armory_image=self.armory.path,
                character_image=self.character.path,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Screenshot import failed", str(exc))
            return

        QMessageBox.information(
            self,
            "Screenshots added",
            "The screenshot pair is safely staged for build analysis.\n\n"
            f"Import ID: {intake.intake_id}\n\n"
            "Nothing was written into your saved builds yet. The analyzer will create a review draft first.",
        )
        self.accept()


def _open_screenshot_import(page) -> None:
    dialog = BuildScreenshotImportDialog(page)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        pending = dialog.service.pending()
        page.status.success(
            f"Screenshot pair staged • {len(pending)} build import(s) waiting for analysis."
        )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    original_build_ui = BuildsPage._build_ui

    def build_ui_with_screenshot_import(self):
        original_build_ui(self)
        button = FoundryButton("📷 Import Screenshots", role=ButtonRole.SECONDARY)
        button.setToolTip(
            "Stage an ESO Armory screenshot plus the matching Character screenshot for build import."
        )
        button.clicked.connect(lambda _checked=False, page=self: _open_screenshot_import(page))
        self.import_screenshots_button = button

        actions = getattr(self, "actions", None)
        layout = actions.layout() if actions is not None else None
        if layout is not None:
            # Existing actions end with Edit / Save / Export.  Put screenshot import
            # first so it reads as an intake action rather than another save/export.
            insert_at = 1 if layout.count() > 1 else 0
            layout.insertWidget(insert_at, button)
        else:
            self.header.add_context_widget(button)

    BuildsPage._build_ui = build_ui_with_screenshot_import
    _INSTALLED = True
