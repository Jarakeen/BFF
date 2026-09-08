from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.accessibility_preferences import VISUAL_THEME_RYLO
from services.stickerbook_service import (
    STICKERBOOK_BUCKETS,
    StickerbookPiece,
    StickerbookService,
)
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.ux_icons import set_button_icon


@dataclass(frozen=True)
class StickerbookTheme:
    key: str
    title: str
    accent: str
    accent_soft: str
    panel: str
    panel_alt: str
    border: str
    text: str
    muted: str
    success: str
    warning: str
    meter_background: str


BFF_THEME = StickerbookTheme(
    key="bff",
    title="#D9B977",
    accent="#59AEB3",
    accent_soft="#2F7A80",
    panel="rgba(12, 31, 34, 218)",
    panel_alt="rgba(19, 54, 58, 226)",
    border="#765D35",
    text="#E5D8BD",
    muted="#7EB6B5",
    success="#63C98B",
    warning="#D2A95A",
    meter_background="#09171A",
)

RYLO_THEME = StickerbookTheme(
    key="rylo",
    title="#D7CDBD",
    accent="#A72A30",
    accent_soft="#75272B",
    panel="rgba(15, 17, 20, 236)",
    panel_alt="rgba(28, 29, 33, 240)",
    border="#48494E",
    text="#D8D0C2",
    muted="#A39C92",
    success="#B88A3C",
    warning="#B88A3C",
    meter_background="#090B0E",
)

_BUCKETS = ("All", *STICKERBOOK_BUCKETS)


def _theme() -> StickerbookTheme:
    app = QApplication.instance()
    if app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO:
        return RYLO_THEME
    return BFF_THEME


def _percent(collected: int, total: int) -> int:
    return round(100 * collected / total) if total else 0


class StickerbookPage(FoundryPage):
    """Profile-aware ESO set-collection tracker backed by canonical gear pieces."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = StickerbookService(get_data_dir() / "eso.db")
        self.theme = _theme()
        self.profile_id = "Default"
        self._rows: list[dict] = []
        self._selected_set_id: int | None = None
        self._piece_checks: list[QCheckBox] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Stickerbook",
            subtitle="Track collected armor, weapons, and jewelry by set, then see exactly what is still missing.",
            department="COLLECTIONS • STICKERBOOK",
        )
        self.set_header(self.header)

        self.profile = QComboBox()
        self.profile.setEditable(True)
        self.profile.setMinimumWidth(150)
        self.profile.currentTextChanged.connect(self._profile_changed)
        self.header.add_context_widget(self._context("PROFILE", self.profile))

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search sets, sources, categories...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_sets)
        self.header.add_context_widget(self._context("SEARCH", self.search))

        self.export_button = QPushButton("Export")
        set_button_icon(self.export_button, "download", 15)
        self.export_button.clicked.connect(self._export)
        self.header.add_context_widget(self.export_button)

        self.summary_row = QHBoxLayout()
        self.summary_row.setSpacing(7)
        self.summary_cards: dict[str, tuple[QLabel, QLabel, QProgressBar, QFrame]] = {}
        for bucket in ("All", "Arena", "Dungeon", "Trial", "Overland", "PvP"):
            frame = QFrame()
            frame.setProperty("stickerSummary", True)
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(10, 7, 10, 7)
            layout.setSpacing(3)
            title = QLabel("Overall Progress" if bucket == "All" else bucket)
            title.setProperty("sidebarHeading", True)
            count = QLabel("0 / 0")
            count.setProperty("stickerSummaryCount", True)
            percent = QLabel("0%")
            percent.setAlignment(Qt.AlignmentFlag.AlignRight)
            meter = QProgressBar()
            meter.setRange(0, 100)
            meter.setTextVisible(False)
            meter.setFixedHeight(9)
            top = QHBoxLayout()
            top.addWidget(count)
            top.addStretch(1)
            top.addWidget(percent)
            layout.addWidget(title)
            layout.addLayout(top)
            layout.addWidget(meter)
            self.summary_cards[bucket] = (count, percent, meter, frame)
            self.summary_row.addWidget(frame, 2 if bucket == "All" else 1)
        self.workspace_layout.addLayout(self.summary_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = FoundryCard("Set Catalog", "collections")
        left.setMinimumWidth(390)
        left.setMaximumWidth(590)
        filter_row = QHBoxLayout()
        self.bucket = QComboBox()
        self.bucket.addItems(_BUCKETS)
        self.bucket.currentTextChanged.connect(self._filter_sets)
        self.sort = QComboBox()
        self.sort.addItems(("Name (A-Z)", "Most Complete", "Least Complete"))
        self.sort.currentIndexChanged.connect(self._filter_sets)
        filter_row.addWidget(self.bucket, 1)
        filter_row.addWidget(self.sort, 1)
        left.addLayout(filter_row)
        self.results = QListWidget()
        self.results.currentItemChanged.connect(self._show_selected)
        left.addWidget(self.results)
        splitter.addWidget(left)

        right = FoundryCard("Set Details", "open-book")
        detail_host = QWidget()
        detail_layout = QVBoxLayout(detail_host)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(8)

        heading = QHBoxLayout()
        name_block = QVBoxLayout()
        self.set_name = QLabel("Select a set")
        self.set_name.setProperty("heroTitle", True)
        self.set_source = QLabel()
        self.set_source.setWordWrap(True)
        name_block.addWidget(self.set_name)
        name_block.addWidget(self.set_source)
        heading.addLayout(name_block, 1)
        progress_block = QVBoxLayout()
        self.set_count = QLabel("0 / 0")
        self.set_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.set_percent = QLabel("0%")
        self.set_percent.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.set_progress = QProgressBar()
        self.set_progress.setRange(0, 100)
        self.set_progress.setTextVisible(False)
        self.set_progress.setFixedWidth(170)
        progress_block.addWidget(self.set_count)
        progress_block.addWidget(self.set_percent)
        progress_block.addWidget(self.set_progress)
        heading.addLayout(progress_block)
        detail_layout.addLayout(heading)

        self.bonus_box = QLabel("Canonical set bonuses will appear here.")
        self.bonus_box.setWordWrap(True)
        self.bonus_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.bonus_box.setProperty("stickerBonusBox", True)
        detail_layout.addWidget(self.bonus_box)

        piece_scroll = QScrollArea()
        piece_scroll.setWidgetResizable(True)
        piece_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.piece_host = QWidget()
        self.piece_layout = QVBoxLayout(self.piece_host)
        self.piece_layout.setContentsMargins(0, 0, 0, 0)
        self.piece_layout.setSpacing(8)
        self.piece_layout.addStretch(1)
        piece_scroll.setWidget(self.piece_host)
        detail_layout.addWidget(piece_scroll, 1)

        right.addWidget(detail_host)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        self.add_workspace(splitter)

        self.status = FoundryStatusBar()
        self.set_status(self.status)
        self._apply_theme()

    @staticmethod
    def _context(label: str, widget: QWidget) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        title = QLabel(label)
        title.setProperty("sidebarHeading", True)
        layout.addWidget(title)
        layout.addWidget(widget)
        return host

    def _apply_theme(self) -> None:
        theme = self.theme
        self.setStyleSheet(
            "QFrame[stickerSummary='true'] {"
            f"background:{theme.panel}; border:1px solid {theme.border}; border-radius:4px;"
            "}"
            "QFrame[stickerPieceGroup='true'] {"
            f"background:{theme.panel}; border:1px solid {theme.border}; border-radius:4px;"
            "}"
            "QLabel[stickerSummaryCount='true'] {"
            f"color:{theme.text}; font-size:15px; font-weight:700;"
            "}"
            "QLabel[stickerBonusBox='true'] {"
            f"background:{theme.panel}; color:{theme.text}; border:1px solid {theme.border}; "
            "border-radius:4px; padding:10px;"
            "}"
            "QProgressBar {"
            f"background:{theme.meter_background}; border:1px solid {theme.border}; border-radius:4px;"
            "}"
            "QProgressBar::chunk {"
            f"background:{theme.accent}; border-radius:3px;"
            "}"
            "QListWidget::item { padding:7px; }"
            "QListWidget::item:selected {"
            f"background:{theme.panel_alt}; color:{theme.title}; border-left:3px solid {theme.accent};"
            "}"
            "QCheckBox {"
            f"color:{theme.text}; spacing:7px; padding:3px;"
            "}"
        )

    def showEvent(self, event) -> None:
        current = _theme()
        if current.key != self.theme.key:
            self.theme = current
            self._apply_theme()
            self.refresh()
        super().showEvent(event)

    def set_profile(self, profile_id: str) -> None:
        value = str(profile_id or "Default").strip() or "Default"
        self.profile_id = value
        if self.profile.findText(value) < 0:
            self.profile.addItem(value)
        self.profile.blockSignals(True)
        self.profile.setCurrentText(value)
        self.profile.blockSignals(False)
        self.refresh()

    def _profile_changed(self, value: str) -> None:
        value = str(value or "Default").strip() or "Default"
        if value == self.profile_id:
            return
        self.profile_id = value
        self.refresh()

    def refresh(self) -> None:
        selected = self._selected_set_id
        self.profile.blockSignals(True)
        current = self.profile_id
        profiles = self.service.profiles()
        if current not in profiles:
            profiles.append(current)
        self.profile.clear()
        self.profile.addItems(sorted(set(profiles), key=str.casefold))
        self.profile.setCurrentText(current)
        self.profile.blockSignals(False)

        self._rows = self.service.sets(self.profile_id)
        self._update_summary()
        self._filter_sets()
        if selected is not None:
            for index in range(self.results.count()):
                item = self.results.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == selected:
                    self.results.setCurrentItem(item)
                    break
        self.status.info(
            f"Stickerbook ready • {len(self._rows)} set(s) • profile: {self.profile_id}."
        )

    def _update_summary(self) -> None:
        for bucket, (count, percent, meter, _frame) in self.summary_cards.items():
            collected, total = self.service.summary(self.profile_id, None if bucket == "All" else bucket)
            value = _percent(collected, total)
            count.setText(f"{collected:,} / {total:,}")
            percent.setText(f"{value}%")
            meter.setValue(value)

    def _filtered_rows(self) -> list[dict]:
        query = self.search.text().strip().casefold()
        bucket = self.bucket.currentText()
        rows = [
            row for row in self._rows
            if (bucket == "All" or row["bucket"] == bucket)
            and (
                not query
                or query in " ".join((row["name"], row["bucket"], row["source"], row["category"])).casefold()
            )
        ]
        mode = self.sort.currentText()
        if mode == "Most Complete":
            rows.sort(key=lambda row: (-(row["collected"] / row["total"] if row["total"] else 0), row["name"].casefold()))
        elif mode == "Least Complete":
            rows.sort(key=lambda row: ((row["collected"] / row["total"] if row["total"] else 0), row["name"].casefold()))
        else:
            rows.sort(key=lambda row: row["name"].casefold())
        return rows

    def _filter_sets(self, *_args) -> None:
        current_id = self._selected_set_id
        self.results.blockSignals(True)
        self.results.clear()
        restore = -1
        for index, row in enumerate(self._filtered_rows()):
            value = _percent(row["collected"], row["total"])
            source = row["source"] or row["bucket"]
            item = QListWidgetItem(
                f"{row['name']}\n{source}   •   {row['collected']} / {row['total']}   ({value}%)"
            )
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            item.setToolTip(f"{row['bucket']} • {row['source'] or 'Source not classified'}")
            self.results.addItem(item)
            if row["id"] == current_id:
                restore = index
        self.results.blockSignals(False)
        if restore >= 0:
            self.results.setCurrentRow(restore)
        elif self.results.count():
            self.results.setCurrentRow(0)
        else:
            self._clear_details("No matching sets")

    def _clear_details(self, title: str = "Select a set") -> None:
        self._selected_set_id = None
        self.set_name.setText(title)
        self.set_source.clear()
        self.set_count.setText("0 / 0")
        self.set_percent.setText("0%")
        self.set_progress.setValue(0)
        self.bonus_box.setText("No set selected.")
        self._replace_piece_groups([])

    def _show_selected(self, current: QListWidgetItem | None, _previous=None) -> None:
        if current is None:
            return
        set_id = int(current.data(Qt.ItemDataRole.UserRole))
        row = next((row for row in self._rows if row["id"] == set_id), None)
        if row is None:
            return
        self._selected_set_id = set_id
        self.set_name.setText(row["name"].upper())
        source_bits = [row["bucket"]]
        if row["source"]:
            source_bits.append(row["source"])
        self.set_source.setText(" • ".join(source_bits))
        value = _percent(row["collected"], row["total"])
        self.set_count.setText(f"{row['collected']} / {row['total']}")
        self.set_percent.setText(f"{value}%")
        self.set_progress.setValue(value)

        bonuses = self.service.bonuses(set_id)
        if bonuses:
            self.bonus_box.setText("\n".join(f"({count} items) {description}" for count, description in bonuses))
        else:
            self.bonus_box.setText("No canonical bonus records are available for this set yet.")

        pieces = self.service.pieces(set_id, self.profile_id)
        self._replace_piece_groups(pieces)

    def _replace_piece_groups(self, pieces: list[StickerbookPiece]) -> None:
        while self.piece_layout.count():
            item = self.piece_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._piece_checks.clear()

        groups = {"Armor": [], "Weapons": [], "Jewelry": [], "Other": []}
        for piece in pieces:
            groups.setdefault(piece.group, []).append(piece)

        for group_name in ("Armor", "Weapons", "Jewelry", "Other"):
            group_pieces = groups.get(group_name) or []
            if not group_pieces:
                continue
            frame = QFrame()
            frame.setProperty("stickerPieceGroup", True)
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(8, 6, 8, 6)
            title = QLabel(f"{group_name.upper()}   {sum(piece.collected for piece in group_pieces)} / {len(group_pieces)}")
            title.setProperty("sidebarHeading", True)
            layout.addWidget(title)
            grid = QGridLayout()
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(3)
            for column in range(3):
                grid.setColumnStretch(column, 1)
            for index, piece in enumerate(group_pieces):
                checkbox = QCheckBox(piece.label)
                checkbox.setChecked(piece.collected)
                checkbox.toggled.connect(
                    lambda checked, p=piece: self._piece_toggled(p, checked)
                )
                self._piece_checks.append(checkbox)
                grid.addWidget(checkbox, index // 3, index % 3)
            layout.addLayout(grid)
            self.piece_layout.addWidget(frame)
        self.piece_layout.addStretch(1)

    def _piece_toggled(self, piece: StickerbookPiece, checked: bool) -> None:
        self.service.set_collected(self.profile_id, piece.set_id, piece.piece_key, checked)
        self._rows = self.service.sets(self.profile_id)
        self._update_summary()
        self._filter_sets()
        for index in range(self.results.count()):
            item = self.results.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == piece.set_id:
                self.results.setCurrentItem(item)
                break
        self.status.success(f"Stickerbook updated • {piece.label} {'collected' if checked else 'marked missing'}.")

    def _export(self) -> None:
        filename, _selected = QFileDialog.getSaveFileName(
            self,
            "Export Stickerbook",
            str(Path.home() / "BFF_Stickerbook.csv"),
            "CSV Files (*.csv)",
        )
        if not filename:
            return
        target = self.service.export_csv(filename, self.profile_id)
        self.status.success(f"Stickerbook exported to {target}.")
