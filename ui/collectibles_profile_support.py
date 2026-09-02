from __future__ import annotations

"""Profile-aware UI support for the Collectibles workspace."""

from PySide6.QtWidgets import QComboBox, QInputDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from services.profiled_collectible_service import ProfiledCollectibleService

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import collectibles_page

    # Swap the page's service constructor before any CollectiblesPage instance
    # is created. The canonical catalog/service API remains otherwise intact.
    collectibles_page.EsoCollectibleDatabaseService = ProfiledCollectibleService

    original_build_ui = collectibles_page.CollectiblesPage.build_ui
    original_connect_signals = collectibles_page.CollectiblesPage.connect_signals

    @staticmethod
    def context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def reload_profile_combo(self, selected: str | None = None) -> None:
        active = selected or self.service.active_profile
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self.service.profiles())
        index = self.profile_combo.findText(active)
        self.profile_combo.setCurrentIndex(index if index >= 0 else 0)
        self.profile_combo.blockSignals(False)

    def build_ui_with_profiles(self) -> None:
        original_build_ui(self)

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(150)
        self.profile_combo.setToolTip("Choose whose collectible ownership is displayed.")
        reload_profile_combo(self)
        self.header.add_context_widget(context_field("PROFILE", self.profile_combo))

        self.add_profile_button = QPushButton("+ Profile")
        self.add_profile_button.setToolTip("Add another person/account collectible profile.")
        self.header.add_context_widget(self.add_profile_button)

    def profile_changed(self, profile: str) -> None:
        profile = profile.strip()
        if not profile or profile == self.service.active_profile:
            return
        if self.has_pending_changes():
            reload_profile_combo(self, self.service.active_profile)
            self.status.warning("Save or discard pending collectible changes before switching profiles.")
            return
        self.service.set_active_profile(profile)
        self.current_collectible_id = None
        self._last_clicked_row = None
        self._clear_details()
        self.refresh()
        self.status.info(f"Collectibles profile: {profile}.")

    def add_profile(self) -> None:
        if self.has_pending_changes():
            self.status.warning("Save or discard pending collectible changes before adding a profile.")
            return
        name, accepted = QInputDialog.getText(self, "Add Collectibles Profile", "Profile name")
        if not accepted or not name.strip():
            return
        try:
            profile = self.service.ensure_profile(name)
            self.service.set_active_profile(profile)
        except ValueError as exc:
            self.status.warning(str(exc))
            return
        reload_profile_combo(self, profile)
        self.current_collectible_id = None
        self._clear_details()
        self.refresh()
        self.status.success(f"Collectibles profile ready: {profile}.")

    def connect_signals_with_profiles(self) -> None:
        original_connect_signals(self)
        self.profile_combo.currentTextChanged.connect(lambda text: profile_changed(self, text))
        self.add_profile_button.clicked.connect(lambda: add_profile(self))

    def save_pending_changes_profiled(self) -> None:
        if not self.pending_changes:
            return
        count = self.service.set_owned_batch(
            self.service.active_profile,
            dict(self.pending_changes),
        )
        self.pending_changes.clear()
        self._last_clicked_row = None
        self.status.success(
            f"Saved {count} collectible ownership change{'s' if count != 1 else ''} "
            f"for {self.service.active_profile}."
        )
        self.refresh()

    collectibles_page.CollectiblesPage.build_ui = build_ui_with_profiles
    collectibles_page.CollectiblesPage.connect_signals = connect_signals_with_profiles
    collectibles_page.CollectiblesPage.save_pending_changes = save_pending_changes_profiled
    collectibles_page.CollectiblesPage._reload_profile_combo = reload_profile_combo

    _INSTALLED = True
