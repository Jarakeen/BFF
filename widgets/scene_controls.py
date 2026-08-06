# ==================================================
# Black Feather Foundry
#
# File:
# widgets/scene_controls.py
#
# Purpose:
# Controls for OBS scene management.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal

from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QComboBox,
)


class SceneControls(QWidget):
    """
    Controls for OBS scene operations.
    """

    sceneChanged = Signal(str)
    refreshRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Controls
        #

        self.scene = QComboBox()

        self.switch_button = QPushButton(
            "Switch Scene"
        )

        self.refresh_button = QPushButton(
            "Refresh"
        )

        #
        # Layout
        #

        form = QFormLayout()

        form.addRow(
            "Current Scene",
            self.scene,
        )

        buttons = QHBoxLayout()

        buttons.addWidget(
            self.switch_button
        )

        buttons.addWidget(
            self.refresh_button
        )

        buttons.addStretch()

        layout = QFormLayout(self)

        layout.addRow(form)

        layout.addRow(buttons)

        #
        # Signals
        #

        self.switch_button.clicked.connect(
            self._emit_scene_changed
        )

        self.refresh_button.clicked.connect(
            self.refreshRequested.emit
        )

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_scenes(
        self,
        scenes: list[str],
    ):
        """
        Populate the scene list.
        """

        self.scene.clear()

        self.scene.addItems(
            sorted(scenes)
        )

    @property
    def current_scene(self) -> str:
        """
        Return the selected scene.
        """

        return self.scene.currentText()

    # --------------------------------------------------
    # Private
    # --------------------------------------------------

    def _emit_scene_changed(self):

        self.sceneChanged.emit(
            self.current_scene
        )