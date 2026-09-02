from __future__ import annotations

"""Keep the Build Editor inside the existing Builds page surface.

The former editor path used a top-level ``QDialog``. On Windows that native
surface can briefly paint with the platform default background before Qt has
finished polishing the themed child widgets. For photosensitive users, even a
single bright frame is unacceptable. This compatibility layer avoids creating
a new native window at all: the editor is constructed offscreen, loaded, then
swapped into the already-dark Foundry page.
"""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QVBoxLayout, QWidget


DARK_SURFACE = "#0C171B"
_INSTALLED = False


def _force_dark_surface(widget: QWidget) -> None:
    widget.setAutoFillBackground(True)
    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(DARK_SURFACE))
    widget.setPalette(palette)
    widget.setStyleSheet(f"background-color: {DARK_SURFACE};")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    def finish_inline_edit(self, save: bool) -> None:
        editor = getattr(self, "_inline_build_editor", None)
        host = getattr(self, "_inline_build_editor_host", None)
        if editor is None or host is None:
            return

        if save and self.roster.Members:
            original = self.roster.Members[self.selected_index]
            updated = editor.model
            updated.ScribedSkills = list(getattr(original, "ScribedSkills", []))
            self.roster.Members[self.selected_index] = updated
            self._save()
            self._refresh_roster()

        host.hide()
        self.workspace_layout.removeWidget(host)
        host.deleteLater()
        self._inline_build_editor = None
        self._inline_build_editor_host = None

        self.splitter.show()
        if self.actions is not None:
            self.actions.show()
        self.workspace_scroll.verticalScrollBar().setValue(
            getattr(self, "_inline_build_editor_previous_scroll", 0)
        )

    def edit_selected_inline(self) -> None:
        if not self.roster.Members:
            return
        if getattr(self, "_inline_build_editor_host", None) is not None:
            return

        build = self.roster.Members[self.selected_index]

        # Build and populate everything before changing what the user can see.
        # The current dark Builds page therefore remains on screen throughout
        # the potentially expensive editor construction work.
        host = QWidget(self.workspace_widget)
        host.setObjectName("inlineBuildEditorHost")
        _force_dark_surface(host)
        host.setVisible(False)

        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        editor = self._editor(build)
        _force_dark_surface(editor)
        editor.load(build)
        layout.addWidget(editor, 1)

        self._inline_build_editor = editor
        self._inline_build_editor_host = host
        self._inline_build_editor_previous_scroll = self.workspace_scroll.verticalScrollBar().value()

        editor.saveRequested.connect(lambda: finish_inline_edit(self, True))
        editor.cancelRequested.connect(lambda: finish_inline_edit(self, False))

        # Add the fully prepared editor to the existing page before hiding the
        # normal roster view. No top-level window is created at any point.
        self.workspace_layout.addWidget(host, 1)
        self.splitter.hide()
        if self.actions is not None:
            self.actions.hide()
        self.workspace_scroll.verticalScrollBar().setValue(0)
        host.show()
        host.raise_()

    BuildsPage._edit_selected = edit_selected_inline
    BuildsPage._finish_inline_build_edit = finish_inline_edit
    _INSTALLED = True
