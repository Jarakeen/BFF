from __future__ import annotations

"""Low-friction Discord profile screenshot intake for Personnel.

This dialog deliberately does not save Personnel records. It keeps the screenshot
visible while the raid lead transcribes or corrects visible identity fields, then
prefills the existing RosterRecord. The normal Personnel Save action remains the
only persistence boundary.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class DiscordProfileScreenshotDialog(QDialog):
    def __init__(self, record, image_path: str | Path, parent=None) -> None:
        super().__init__(parent)
        self.record = record
        self.image_path = Path(image_path)
        self.setWindowTitle("Discord Profile Screenshot Intake")
        self.resize(1120, 720)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        preview_host = QWidget()
        preview_layout = QVBoxLayout(preview_host)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.preview.setMinimumWidth(520)
        pixmap = QPixmap(str(self.image_path))
        if pixmap.isNull():
            self.preview.setText("Screenshot could not be loaded.")
        else:
            self.preview.setPixmap(
                pixmap.scaled(
                    620,
                    880,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        preview_layout.addWidget(self.preview)
        preview_layout.addStretch(1)
        preview_scroll.setWidget(preview_host)
        root.addWidget(preview_scroll, 3)

        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 4, 8, 4)
        panel_layout.setSpacing(10)

        title = QLabel("QUICK PERSONNEL INTAKE")
        title.setProperty("sidebarHeading", True)
        panel_layout.addWidget(title)

        note = QLabel(
            "Use the screenshot as the source. Nothing is saved automatically. "
            "Confirm what is visibly present, then use the normal Personnel Save button."
        )
        note.setWordWrap(True)
        note.setProperty("muted", True)
        panel_layout.addWidget(note)

        self.xbox = QLineEdit(record.player_name.text())
        self.xbox.setPlaceholderText("Xbox gamertag")
        self.discord = QLineEdit(record.discord_name.text())
        self.discord.setPlaceholderText("Discord display name / username")
        self.youtube = QLineEdit(record.youtube.text())
        self.youtube.setPlaceholderText("YouTube channel or handle")
        self.twitch = QLineEdit(record.twitch.text())
        self.twitch.setPlaceholderText("Twitch channel or handle")

        form = QFormLayout()
        form.addRow("Xbox Gamertag", self.xbox)
        form.addRow("Discord", self.discord)
        form.addRow("YouTube", self.youtube)
        form.addRow("Twitch", self.twitch)
        panel_layout.addLayout(form)

        helper = QLabel(
            "Tip: Discord screenshots often show the display name and username. "
            "If the person's Xbox gamertag is visible in their profile/about text, copy it here too."
        )
        helper.setWordWrap(True)
        helper.setProperty("muted", True)
        panel_layout.addWidget(helper)
        panel_layout.addStretch(1)

        actions = QHBoxLayout()
        cancel = QPushButton("Cancel")
        use = QPushButton("Use These Details")
        use.setProperty("primary", True)
        cancel.clicked.connect(self.reject)
        use.clicked.connect(self.accept)
        actions.addStretch(1)
        actions.addWidget(cancel)
        actions.addWidget(use)
        panel_layout.addLayout(actions)

        root.addWidget(panel, 2)

    def apply_to_record(self) -> None:
        self.record.player_name.setText(self.xbox.text().strip())
        self.record.discord_name.setText(self.discord.text().strip())
        self.record.youtube.setText(self.youtube.text().strip())
        self.record.twitch.setText(self.twitch.text().strip())


def import_discord_profile_screenshot(page) -> bool:
    filename, _ = QFileDialog.getOpenFileName(
        page,
        "Choose Discord Profile Screenshot",
        "",
        "Images (*.png *.jpg *.jpeg *.webp)",
    )
    if not filename:
        return False

    dialog = DiscordProfileScreenshotDialog(page.record, filename, parent=page)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False

    dialog.apply_to_record()
    status = getattr(page, "status", None)
    if status is not None:
        status.info(
            "Discord screenshot details filled into the Player record. "
            "Review them, then use Save when ready."
        )
    return True


__all__ = [
    "DiscordProfileScreenshotDialog",
    "import_discord_profile_screenshot",
]
