from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.learned_motif_service import LearnedMotifService
from services.learned_recipe_service import LearnedRecipeService
from services.lorebook_service import LorebookService
from services.profiled_collectible_service import ProfiledCollectibleService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_sidebar import CORE_NAV_SECTIONS
from ui.components.foundry_status_bar import FoundryStatusBar


@dataclass(frozen=True)
class CategoryProgress:
    label: str
    route: str
    owned: int
    total: int
    available: bool = True

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.owned)

    @property
    def percent(self) -> int:
        if self.total <= 0:
            return 0
        return round((self.owned / self.total) * 100)


class CollectiblesDashboard(QWidget):
    """Profile-aware overview for every collection category in the sidebar."""

    routeRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        data_dir = get_data_dir()
        database = data_dir / "eso.db"
        self.collectibles = ProfiledCollectibleService(database)
        self.recipes = LearnedRecipeService(database)
        self.motifs = LearnedMotifService(database)
        self.lorebooks = LorebookService(database)
        self._profile = "Default"
        self._rows: list[CategoryProgress] = []
        self._build_ui()
        self.refresh()

    @staticmethod
    def _collection_routes() -> list[tuple[str, str]]:
        for section in CORE_NAV_SECTIONS:
            if isinstance(section, dict) and section.get("label") == "Collections":
                return list(section.get("children", ()))
        return []

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        self.header = FoundryHeader(
            title="Collections",
            subtitle="A field-office view of everything acquired, learned, found, and still lurking somewhere in Tamriel.",
            department="Collections",
            icon="collections",
        )
        root.addWidget(self.header)

        controls = FoundryCard("COLLECTION OVERVIEW")
        control_row = QHBoxLayout()
        self.profile_label = QLabel("Profile: Default")
        self.profile_label.setProperty("sidebarHeading", True)
        control_row.addWidget(self.profile_label)
        control_row.addStretch(1)
        sort_label = QLabel("SORT")
        sort_label.setProperty("muted", True)
        control_row.addWidget(sort_label)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(("Menu Order", "Closest to Complete", "Most Remaining"))
        self.sort_combo.currentTextChanged.connect(self._render_categories)
        control_row.addWidget(self.sort_combo)
        controls.addLayout(control_row)

        self.overall_text = QLabel("0 / 0 recorded")
        self.overall_text.setProperty("pageTitle", True)
        controls.addWidget(self.overall_text)
        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setTextVisible(True)
        controls.addWidget(self.overall_bar)
        self.overall_note = QLabel("")
        self.overall_note.setWordWrap(True)
        self.overall_note.setProperty("muted", True)
        controls.addWidget(self.overall_note)
        root.addWidget(controls)

        spotlight_row = QHBoxLayout()
        spotlight_row.setSpacing(12)
        self.finish_card = FoundryCard("NEAREST FINISH LINE")
        self.finish_text = QLabel("Nothing to report yet.")
        self.finish_text.setWordWrap(True)
        self.finish_card.addWidget(self.finish_text)
        spotlight_row.addWidget(self.finish_card, 1)

        self.long_road_card = FoundryCard("THE LONG ROAD")
        self.long_road_text = QLabel("Nothing to report yet.")
        self.long_road_text.setWordWrap(True)
        self.long_road_card.addWidget(self.long_road_text)
        spotlight_row.addWidget(self.long_road_card, 1)
        root.addLayout(spotlight_row)

        self.category_card = FoundryCard("COLLECTION DEPARTMENTS")
        self.category_host = QWidget()
        self.category_grid = QGridLayout(self.category_host)
        self.category_grid.setContentsMargins(0, 0, 0, 0)
        self.category_grid.setHorizontalSpacing(10)
        self.category_grid.setVerticalSpacing(10)
        self.category_card.addWidget(self.category_host)
        root.addWidget(self.category_card, 1)

        self.status = FoundryStatusBar()
        root.addWidget(self.status)

    def set_profile(self, profile: str) -> None:
        profile = " ".join(str(profile or "").strip().split()) or "Default"
        if profile == self._profile:
            self.refresh()
            return
        self._profile = profile
        self.refresh()

    def _sync_profile(self) -> None:
        for service in (self.collectibles, self.recipes, self.motifs, self.lorebooks):
            setter = getattr(service, "set_active_profile", None)
            if callable(setter):
                setter(self._profile)

    def _progress_for(self, label: str, route: str) -> CategoryProgress:
        try:
            if label in {"Recipes", "Furnishing Plans"}:
                if not self.recipes.available:
                    return CategoryProgress(label, route, 0, 0, False)
                owned, total = self.recipes.progress_summary(label)
            elif label == "Motifs":
                if not self.motifs.available:
                    return CategoryProgress(label, route, 0, 0, False)
                owned, total = self.motifs.progress_summary()
            elif label == "Lorebooks":
                if not self.lorebooks.available:
                    return CategoryProgress(label, route, 0, 0, False)
                owned, total = self.lorebooks.progress_summary()
            else:
                if not self.collectibles.available:
                    return CategoryProgress(label, route, 0, 0, False)
                owned, total = self.collectibles.progress_summary(label)
            return CategoryProgress(label, route, int(owned), int(total), True)
        except (KeyError, LookupError):
            return CategoryProgress(label, route, 0, 0, False)

    def refresh(self) -> None:
        self._sync_profile()
        self.profile_label.setText(f"Profile: {self._profile}")
        self._rows = [self._progress_for(label, route) for label, route in self._collection_routes()]

        available_rows = [row for row in self._rows if row.available and row.total > 0]
        owned = sum(row.owned for row in available_rows)
        total = sum(row.total for row in available_rows)
        percent = round((owned / total) * 100) if total else 0
        remaining = max(0, total - owned)

        self.overall_text.setText(f"{owned:,} / {total:,} recorded")
        self.overall_bar.setValue(percent)
        self.overall_bar.setFormat(f"{percent}% complete")
        self.overall_note.setText(
            f"{remaining:,} entries remain across {len(available_rows)} tracked departments. "
            "This number is informational, not a legally binding obligation to collect another guar."
        )

        candidates = [row for row in available_rows if row.remaining > 0]
        if candidates:
            nearest = min(candidates, key=lambda row: (row.remaining, -row.percent, row.label.casefold()))
            self.finish_text.setText(
                f"{nearest.label} · {nearest.owned:,}/{nearest.total:,} · only {nearest.remaining:,} remaining. "
                "Suspiciously achievable."
            )
            longest = max(candidates, key=lambda row: (row.remaining, -row.percent, row.label.casefold()))
            self.long_road_text.setText(
                f"{longest.label} · {longest.owned:,}/{longest.total:,} · {longest.remaining:,} still outstanding. "
                "The Archive has declined to estimate morale."
            )
        else:
            self.finish_text.setText("Everything represented here is complete. This seems statistically rude.")
            self.long_road_text.setText("No outstanding entries in the available catalogs.")

        self._render_categories()
        unavailable = sum(1 for row in self._rows if not row.available)
        suffix = f" · {unavailable} unavailable catalog{'s' if unavailable != 1 else ''}" if unavailable else ""
        self.status.info(
            f"Collections dashboard · {len(available_rows)} tracked departments · {percent}% overall for {self._profile}{suffix}."
        )

    def _sorted_rows(self) -> list[CategoryProgress]:
        mode = self.sort_combo.currentText()
        rows = list(self._rows)
        if mode == "Closest to Complete":
            rows.sort(key=lambda row: (not row.available, row.remaining if row.total else 10**12, -row.percent, row.label.casefold()))
        elif mode == "Most Remaining":
            rows.sort(key=lambda row: (not row.available, -row.remaining, row.label.casefold()))
        return rows

    def _clear_grid(self) -> None:
        while self.category_grid.count():
            item = self.category_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_categories(self, *_args) -> None:
        self._clear_grid()
        rows = self._sorted_rows()
        columns = 3
        for index, row in enumerate(rows):
            tile = FoundryCard(row.label)
            if row.available and row.total > 0:
                summary = QLabel(f"{row.owned:,} / {row.total:,}")
                summary.setProperty("pageTitle", True)
                tile.addWidget(summary)
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(row.percent)
                bar.setFormat(f"{row.percent}%")
                tile.addWidget(bar)
                note = QLabel(f"{row.remaining:,} remaining")
            elif row.available:
                note = QLabel("Catalog is available but currently empty.")
            else:
                note = QLabel("Catalog unavailable in this database.")
            note.setProperty("muted", True)
            note.setWordWrap(True)
            tile.addWidget(note)

            button = QPushButton("Open Collection")
            button.setEnabled(row.available)
            button.clicked.connect(lambda checked=False, route=row.route: self.routeRequested.emit(route))
            tile.addWidget(button)
            self.category_grid.addWidget(tile, index // columns, index % columns)

        for column in range(columns):
            self.category_grid.setColumnStretch(column, 1)
