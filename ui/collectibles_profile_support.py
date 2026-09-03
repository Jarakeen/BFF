from __future__ import annotations

"""Profile-aware UI support for the Collectibles workspace."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.profiled_collectible_service import ProfiledCollectibleService

_INSTALLED = False


def _transparent_dashboard_labels(widget: QWidget) -> None:
    """Keep global theme label surfaces from painting blocks over dashboard art."""
    for label in widget.findChildren(QLabel):
        label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        current = label.styleSheet().rstrip()
        if current and not current.endswith(";"):
            current += ";"
        label.setStyleSheet(current + " background: transparent;")


def _largest_center_art_crop(sheet, index: int):
    """Crop one generated badge by its actual opaque medallion bounds.

    Generated sprite art does not obey an exact mathematical grid. Start with a
    slightly overlapping nominal cell, identify the largest opaque component at
    preview resolution, and crop around that component. Neighbor fragments at
    the edges are therefore ignored while ornaments that extend a little beyond
    the nominal cell remain available.
    """
    if index < 0 or index >= sheet.columns * sheet.rows:
        return None
    if index in sheet._cache:
        return sheet._cache[index]
    sheet._load()
    if sheet._sheet is None or sheet._sheet.isNull():
        return None

    cell_width = sheet._sheet.width() / sheet.columns
    cell_height = sheet._sheet.height() / sheet.rows
    column = index % sheet.columns
    row = index // sheet.columns
    overlap_x = cell_width * 0.10
    overlap_y = cell_height * 0.10
    left = max(0, round(column * cell_width - overlap_x))
    top = max(0, round(row * cell_height - overlap_y))
    right = min(sheet._sheet.width(), round((column + 1) * cell_width + overlap_x))
    bottom = min(sheet._sheet.height(), round((row + 1) * cell_height + overlap_y))
    region = sheet._sheet.copy(left, top, max(1, right - left), max(1, bottom - top))

    preview_size = 128
    preview = region.scaled(
        preview_size,
        preview_size,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,
    ).toImage()
    width = preview.width()
    height = preview.height()
    visited = bytearray(width * height)
    components: list[tuple[int, int, int, int, int]] = []

    for y in range(height):
        for x in range(width):
            offset = y * width + x
            if visited[offset]:
                continue
            visited[offset] = 1
            if preview.pixelColor(x, y).alpha() <= 32:
                continue

            stack = [(x, y)]
            count = 0
            min_x = max_x = x
            min_y = max_y = y
            while stack:
                px, py = stack.pop()
                count += 1
                min_x = min(min_x, px)
                max_x = max(max_x, px)
                min_y = min(min_y, py)
                max_y = max(max_y, py)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx = px + dx
                        ny = py + dy
                        if nx < 0 or ny < 0 or nx >= width or ny >= height:
                            continue
                        noffset = ny * width + nx
                        if visited[noffset]:
                            continue
                        visited[noffset] = 1
                        if preview.pixelColor(nx, ny).alpha() > 32:
                            stack.append((nx, ny))
            components.append((count, min_x, min_y, max_x, max_y))

    if not components:
        sheet._cache[index] = region
        return region

    _, min_x, min_y, max_x, max_y = max(components, key=lambda item: item[0])
    scale_x = region.width() / width
    scale_y = region.height() / height
    pad_x = max(3, round(region.width() * 0.025))
    pad_y = max(3, round(region.height() * 0.025))
    crop_left = max(0, round(min_x * scale_x) - pad_x)
    crop_top = max(0, round(min_y * scale_y) - pad_y)
    crop_right = min(region.width(), round((max_x + 1) * scale_x) + pad_x)
    crop_bottom = min(region.height(), round((max_y + 1) * scale_y) + pad_y)
    cropped = region.copy(
        crop_left,
        crop_top,
        max(1, crop_right - crop_left),
        max(1, crop_bottom - crop_top),
    )
    sheet._cache[index] = cropped
    return cropped


def _rebuild_collectibles_dashboards() -> None:
    """Recreate the dashboard after a runtime visual-theme change."""
    app = QApplication.instance()
    if app is None:
        return

    from ui.collectibles_dashboard_page import CollectiblesDashboardPage

    for window in app.topLevelWidgets():
        pages = getattr(window, "pages", None)
        containers = getattr(window, "page_containers", None)
        stack = getattr(window, "stack", None)
        service = getattr(window, "collectible_service", None)
        wrap_page = getattr(window, "wrap_page", None)
        show_page = getattr(window, "show_page", None)
        if not isinstance(pages, dict) or not isinstance(containers, dict):
            continue
        if stack is None or service is None or not callable(wrap_page):
            continue
        old_container = containers.get("collectibles")
        if old_container is None:
            continue

        new_dashboard = CollectiblesDashboardPage(service)
        if callable(show_page):
            new_dashboard.categoryRequested.connect(
                lambda category, owner=window: owner.show_page(f"collectibles:{category}")
            )
        new_container = wrap_page(new_dashboard)
        was_current = stack.currentWidget() is old_container
        stack.addWidget(new_container)
        stack.removeWidget(old_container)
        old_container.deleteLater()
        pages["collectibles"] = new_dashboard
        containers["collectibles"] = new_container
        if was_current:
            stack.setCurrentWidget(new_container)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import collectibles_dashboard_page, collectibles_page, settings_page

    # Swap the page's service constructor before any CollectiblesPage instance
    # is created. The canonical catalog/service API remains otherwise intact.
    collectibles_page.EsoCollectibleDatabaseService = ProfiledCollectibleService

    original_build_ui = collectibles_page.CollectiblesPage.build_ui
    original_connect_signals = collectibles_page.CollectiblesPage.connect_signals

    # Generated badge sheets are not perfectly cell-aligned. Keep the existing
    # deterministic grid slicer for number sheets, but content-crop badge art.
    original_sprite_cell = collectibles_dashboard_page.SpriteSheet.cell

    def content_aware_sprite_cell(self, index: int):
        if self.path.name.casefold().startswith("badges"):
            return _largest_center_art_crop(self, index)
        return original_sprite_cell(self, index)

    collectibles_dashboard_page.SpriteSheet.cell = content_aware_sprite_cell

    # Global QSS can give QLabel opaque surfaces. Dashboard labels are overlays
    # on their card/frame surfaces and should remain visually transparent.
    original_tile_init = collectibles_dashboard_page.ProgressTile.__init__
    original_dashboard_init = collectibles_dashboard_page.CollectiblesDashboardPage.__init__

    def tile_init_with_transparent_labels(self, *args, **kwargs) -> None:
        original_tile_init(self, *args, **kwargs)
        _transparent_dashboard_labels(self)

    def dashboard_init_with_transparent_labels(self, *args, **kwargs) -> None:
        original_dashboard_init(self, *args, **kwargs)
        _transparent_dashboard_labels(self)

    collectibles_dashboard_page.ProgressTile.__init__ = tile_init_with_transparent_labels
    collectibles_dashboard_page.CollectiblesDashboardPage.__init__ = dashboard_init_with_transparent_labels

    # Rylo/Foundry can be switched live from Settings. The dashboard contains
    # theme-specific inline painting and sprite choices, so rebuild that one
    # page after the ThemeManager has applied the new visual theme. The existing
    # appearance-page contract returns one QWidget; do not assume a (page, layout)
    # tuple because the Rylo theme layer intentionally wraps that builder too.
    original_appearance_page = settings_page.SettingsPage._appearance_page

    def appearance_page_with_dashboard_refresh(self):
        page = original_appearance_page(self)
        combo = getattr(self, "visual_theme_combo", None)
        if combo is not None:
            combo.currentIndexChanged.connect(lambda _index: _rebuild_collectibles_dashboards())
        return page

    settings_page.SettingsPage._appearance_page = appearance_page_with_dashboard_refresh

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
