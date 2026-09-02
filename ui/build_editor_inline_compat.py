from __future__ import annotations

"""Keep the Build Editor inside the existing Builds page surface.

The former editor path used a top-level native dialog. On Windows that surface
could briefly paint with the platform default background before Qt finished
polishing the themed child widgets. For photosensitive users, even a single
bright frame is unacceptable.

The editor now lives in a persistent in-page tab. The normal Builds workspace
remains available in its own tab, so editing never creates another native
window and never traps the user in a hide/show replacement state.
"""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget


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

    original_build_ui = BuildsPage._build_ui

    def build_ui_with_editor_tabs(self) -> None:
        original_build_ui(self)

        # The original page places the roster/detail splitter directly in the
        # workspace. Reparent it into a stable tab container instead. The
        # surrounding FoundryPage and its dark native surface never change.
        self.workspace_layout.removeWidget(self.splitter)

        tabs = QTabWidget(self.workspace_widget)
        tabs.setObjectName("buildWorkspaceTabs")
        tabs.setDocumentMode(True)
        tabs.setMovable(False)
        tabs.setTabsClosable(False)
        _force_dark_surface(tabs)

        tabs.addTab(self.splitter, "Builds")
        self.workspace_layout.addWidget(tabs, 1)

        self.build_tabs = tabs
        self._build_editor = None
        self._build_editor_host = None
        self._build_editor_index = None

    def finish_tab_edit(self, save: bool) -> None:
        editor = getattr(self, "_build_editor", None)
        host = getattr(self, "_build_editor_host", None)
        index = getattr(self, "_build_editor_index", None)
        tabs = getattr(self, "build_tabs", None)
        if editor is None or host is None or tabs is None:
            return

        if save and index is not None and 0 <= index < len(self.roster.Members):
            original = self.roster.Members[index]
            updated = editor.model
            updated.ScribedSkills = list(getattr(original, "ScribedSkills", []))
            self.roster.Members[index] = updated
            self.selected_index = index
            self._save()
            self._refresh_roster()

        tab_index = tabs.indexOf(host)
        if tab_index >= 0:
            tabs.removeTab(tab_index)
        host.deleteLater()

        self._build_editor = None
        self._build_editor_host = None
        self._build_editor_index = None
        self.edit_button.setEnabled(True)
        tabs.setCurrentIndex(0)

    def edit_selected_tab(self) -> None:
        if not self.roster.Members:
            return

        tabs = getattr(self, "build_tabs", None)
        if tabs is None:
            return

        existing = getattr(self, "_build_editor_host", None)
        if existing is not None:
            tabs.setCurrentWidget(existing)
            return

        index = self.selected_index
        if index < 0 or index >= len(self.roster.Members):
            return
        build = self.roster.Members[index]

        # Construct and populate the editor while the existing Builds tab stays
        # visible. Only after the widget is complete do we add and select the
        # editor tab. No top-level/native window is created.
        host = QWidget(tabs)
        host.setObjectName("buildEditorTab")
        _force_dark_surface(host)

        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        editor = self._editor(build)
        _force_dark_surface(editor)
        editor.load(build)
        layout.addWidget(editor, 1)

        self._build_editor = editor
        self._build_editor_host = host
        self._build_editor_index = index

        editor.saveRequested.connect(lambda: finish_tab_edit(self, True))
        editor.cancelRequested.connect(lambda: finish_tab_edit(self, False))

        name = (build.Name or build.Gamertag or "Build").strip() or "Build"
        tabs.addTab(host, f"Edit: {name}")
        tabs.setCurrentWidget(host)
        self.edit_button.setEnabled(False)

    BuildsPage._build_ui = build_ui_with_editor_tabs
    BuildsPage._edit_selected = edit_selected_tab
    BuildsPage._finish_inline_build_edit = finish_tab_edit
    BuildsPage._finish_build_tab_edit = finish_tab_edit
    _INSTALLED = True
