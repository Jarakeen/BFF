from __future__ import annotations

"""Unified Raid Engine dashboard.

This page is deliberately a read-mostly command surface. It mirrors the active
state already owned by Comp Maker, Team Optimization, Coverage, Encounters, and
Performance instead of inventing a second raid model. Navigation actions hand
control back to those canonical workspaces.
"""

from dataclasses import dataclass
import math
import re

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_resource_path
from services.accessibility_preferences import VISUAL_THEME_RYLO
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


RAID_SLOTS = (
    "Main Tank",
    "Off Tank",
    "Healer 1",
    "Healer 2",
    "DD 1",
    "DD 2",
    "DD 3",
    "DD 4",
    "DD 5",
    "DD 6",
    "DD 7",
    "DD 8",
)

COVERAGE_WATCH = tuple(row.display_name for row in DEFAULT_RAID_COVERAGE_PROFILE.requirements if row.required)


@dataclass(frozen=True)
class RaidSlotSnapshot:
    slot: str
    player: str = ""
    eso_class: str = ""
    build: str = ""
    status: str = "OPEN"


@dataclass(frozen=True)
class CoverageSnapshot:
    effects: tuple[tuple[str, str], ...]
    covered: int
    total: int


@dataclass(frozen=True)
class OptimizationSnapshot:
    assigned: int
    saved_builds: int
    coverage_covered: int
    coverage_total: int
    capability_gaps: int
    build_swaps: int
    readiness: int


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_slot_name(value: object) -> str:
    text = _clean(value)
    compact = re.sub(r"\s+", " ", text).strip()
    aliases = {
        "maintank": "Main Tank",
        "main tank": "Main Tank",
        "offtank": "Off Tank",
        "off tank": "Off Tank",
        "healer1": "Healer 1",
        "healer 1": "Healer 1",
        "healer2": "Healer 2",
        "healer 2": "Healer 2",
    }
    key = compact.casefold()
    if key in aliases:
        return aliases[key]
    dd = re.fullmatch(r"(?:dd|dps)\s*(\d+)", key)
    if dd:
        return f"DD {int(dd.group(1))}"
    return compact


def _readiness_score(*, assigned: int, total_slots: int, covered: int, total_coverage: int, capability_gaps: int) -> int:
    """Dashboard-only readiness pulse; not combat math and not an optimization rank."""
    if assigned <= 0 and covered <= 0:
        return 0
    slot_ratio = assigned / max(1, total_slots)
    coverage_ratio = covered / max(1, total_coverage)
    gap_ratio = 1.0 / (1.0 + max(0, capability_gaps))
    score = 0.45 * slot_ratio + 0.35 * coverage_ratio + 0.20 * gap_ratio
    return max(0, min(100, round(score * 100)))


def _table_column(table: QTableWidget, names: tuple[str, ...]) -> int | None:
    wanted = {name.casefold() for name in names}
    for column in range(table.columnCount()):
        item = table.horizontalHeaderItem(column)
        label = _clean(item.text() if item is not None else "").casefold()
        if label in wanted:
            return column
    return None


def _table_text(table: QTableWidget, row: int, column: int | None) -> str:
    if column is None or column < 0 or column >= table.columnCount():
        return ""
    widget = table.cellWidget(row, column)
    if isinstance(widget, QComboBox):
        return _clean(widget.currentText())
    item = table.item(row, column)
    return _clean(item.text() if item is not None else "")


def _build_identity(build) -> tuple[str, str, str]:
    player = _clean(getattr(build, "Name", "") or getattr(build, "Gamertag", ""))
    eso_class = _clean(getattr(build, "EsoClass", ""))
    build_name = _clean(getattr(build, "BuildName", ""))
    return player, eso_class, build_name


class CompositionRingWidget(QWidget):
    """The mockup's 12-chair raid wheel, backed by the supplied decorative art."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._slots = tuple(RaidSlotSnapshot(slot=name) for name in RAID_SLOTS)
        self._oval_path = get_resource_path("assets", "decorative", "raid_engine_oval.png")
        self._star_path = get_resource_path("assets", "decorative", "raid_engine_star.png")
        self._oval = QPixmap(str(self._oval_path)) if self._oval_path.exists() else QPixmap()
        self._star = QPixmap(str(self._star_path)) if self._star_path.exists() else QPixmap()

    @staticmethod
    def _is_rylo() -> bool:
        app = QApplication.instance()
        return bool(app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO)

    def set_slots(self, slots: tuple[RaidSlotSnapshot, ...]) -> None:
        by_name = {_normalize_slot_name(slot.slot): slot for slot in slots}
        self._slots = tuple(by_name.get(name, RaidSlotSnapshot(slot=name)) for name in RAID_SLOTS)
        self.update()

    def _colors(self):
        if self._is_rylo():
            return {
                "gold": QColor("#8C8580"),
                "teal": QColor("#8B0E14"),
                "text": QColor("#D8D0C2"),
                "muted": QColor("#99928A"),
                "tank": QColor("#55717A"),
                "heal": QColor("#63815F"),
                "dd": QColor("#806E42"),
                "open": QColor("#263237"),
                "need": QColor("#8B0E14"),
            }
        return {
            "gold": QColor("#C8A46A"),
            "teal": QColor("#2F7A80"),
            "text": QColor("#E5ECEB"),
            "muted": QColor("#93A7A7"),
            "tank": QColor("#2F7184"),
            "heal": QColor("#4E8B68"),
            "dd": QColor("#B17932"),
            "open": QColor("#18383E"),
            "need": QColor("#C88B39"),
        }

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        colors = self._colors()

        rect = self.rect().adjusted(24, 18, -24, -32)
        cx = rect.center().x()
        cy = rect.center().y() + 8
        rx = rect.width() * 0.40
        ry = rect.height() * 0.37

        # BFF uses the generated art supplied by the user. Rylo receives a neutral
        # theme-safe drawn orbit rather than importing BFF's gold/teal ornament.
        if not self._is_rylo() and not self._oval.isNull():
            target = QRectF(cx - rx * 1.18, cy - ry * 1.35, rx * 2.36, ry * 2.70)
            painter.setOpacity(0.82)
            painter.drawPixmap(target.toRect(), self._oval)
            painter.setOpacity(1.0)
        else:
            painter.setPen(QPen(colors["gold"], 1.25))
            painter.drawEllipse(QRectF(cx - rx, cy - ry, rx * 2, ry * 2))
            painter.setPen(QPen(colors["teal"], 1.0))
            painter.drawEllipse(QRectF(cx - rx * 0.45, cy - ry * 0.48, rx * 0.90, ry * 0.96))

        if not self._is_rylo() and not self._star.isNull():
            star_size = min(rect.width(), rect.height()) * 0.22
            star_rect = QRectF(cx - star_size / 2, cy - star_size / 2, star_size, star_size)
            painter.drawPixmap(star_rect.toRect(), self._star)
        else:
            painter.setPen(QPen(colors["gold"], 2.0))
            for angle in range(0, 360, 45):
                radians = math.radians(angle)
                painter.drawLine(
                    int(cx), int(cy),
                    int(cx + math.cos(radians) * 42),
                    int(cy + math.sin(radians) * 42),
                )

        assigned = sum(1 for slot in self._slots if slot.status == "SAVED")
        needs = sum(1 for slot in self._slots if slot.status == "NEEDS BUILD")
        painter.setPen(colors["gold"])
        font = painter.font()
        font.setBold(True)
        font.setPointSize(max(10, font.pointSize()))
        painter.setFont(font)
        painter.drawText(QRectF(cx - 80, cy + 44, 160, 24), Qt.AlignmentFlag.AlignCenter, f"{assigned} / 12")
        font.setBold(False)
        font.setPointSize(max(8, font.pointSize() - 2))
        painter.setFont(font)
        painter.drawText(QRectF(cx - 80, cy + 64, 160, 20), Qt.AlignmentFlag.AlignCenter, "ASSIGNED")

        # Place tanks/healers on the upper arc and DDs around the lower arc, as in
        # the approved mockup. The decorative oval remains art; the live state is
        # painted independently so nothing is baked into the PNG.
        angles = (-102, -78, -146, -178, -210, -236, -258, -278, -300, -322, -342, -18)
        role_letters = {"Tank": "T", "Healer": "H", "DD": "D"}
        for slot, degrees in zip(self._slots, angles):
            radians = math.radians(degrees)
            x = cx + math.cos(radians) * rx
            y = cy + math.sin(radians) * ry
            role = "Tank" if "Tank" in slot.slot else "Healer" if "Healer" in slot.slot else "DD"
            base = colors["tank"] if role == "Tank" else colors["heal"] if role == "Healer" else colors["dd"]
            fill = base if slot.status == "SAVED" else colors["need"] if slot.status == "NEEDS BUILD" else colors["open"]

            painter.setBrush(fill)
            painter.setPen(QPen(colors["gold"] if slot.status != "SAVED" else base.lighter(150), 1.6))
            painter.drawEllipse(QRectF(x - 16, y - 16, 32, 32))
            painter.setPen(colors["text"])
            font = painter.font()
            font.setBold(True)
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(QRectF(x - 16, y - 16, 32, 32), Qt.AlignmentFlag.AlignCenter, role_letters[role])

            painter.setPen(colors["text"])
            font.setBold(False)
            font.setPointSize(8)
            painter.setFont(font)
            label_rect = QRectF(x - 58, y - 40, 116, 18)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, slot.slot)
            detail = slot.player or ("Needs build" if slot.status == "NEEDS BUILD" else "Open")
            painter.setPen(colors["muted"])
            painter.drawText(QRectF(x - 62, y + 18, 124, 30), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, detail)

        painter.setPen(colors["muted"])
        summary = f"{assigned}/12 assigned   ·   {needs}/12 needs build   ·   {12 - assigned - needs}/12 open"
        painter.drawText(QRectF(rect.left(), rect.bottom() - 10, rect.width(), 28), Qt.AlignmentFlag.AlignCenter, summary)


class ReadinessRingWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.value = 0
        self.setFixedSize(126, 126)

    def setValue(self, value: int) -> None:  # noqa: N802 - Qt style API
        self.value = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(12, 12, self.width() - 24, self.height() - 24)
        painter.setPen(QPen(QColor("#18383E"), 11))
        painter.drawArc(rect, 0, 360 * 16)
        painter.setPen(QPen(QColor("#59A66E"), 11))
        painter.drawArc(rect, 90 * 16, -round(360 * 16 * self.value / 100))
        painter.setPen(QColor("#C8A46A"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(18)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.value}%")
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(QRectF(0, self.height() * 0.62, self.width(), 22), Qt.AlignmentFlag.AlignCenter, "PLAN")


class EncounterMiniMap(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(220, 150)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = self.rect().adjusted(18, 12, -18, -12)
        painter.setPen(QPen(QColor("#765D35"), 1.4))
        painter.drawRoundedRect(r, 12, 12)
        painter.setPen(QPen(QColor("#2F5559"), 1.0))
        painter.drawEllipse(QRectF(r.center().x() - 58, r.center().y() - 40, 116, 80))
        nodes = (
            (0.50, 0.27, "T", "#2F7184"),
            (0.26, 0.52, "H", "#4E8B68"),
            (0.74, 0.52, "H", "#4E8B68"),
            (0.50, 0.75, "D", "#B17932"),
        )
        for fx, fy, letter, color in nodes:
            x = r.left() + r.width() * fx
            y = r.top() + r.height() * fy
            painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor("#C8A46A"), 1.1))
            painter.drawEllipse(QRectF(x - 11, y - 11, 22, 22))
            painter.setPen(QColor("#E5ECEB"))
            painter.drawText(QRectF(x - 11, y - 11, 22, 22), Qt.AlignmentFlag.AlignCenter, letter)
        x, y = r.center().x(), r.center().y()
        painter.setBrush(QColor("#6E302A"))
        painter.setPen(QPen(QColor("#C88B59"), 1.5))
        painter.drawEllipse(QRectF(x - 23, y - 23, 46, 46))
        painter.setPen(QColor("#E5ECEB"))
        painter.drawText(QRectF(x - 23, y - 23, 46, 46), Qt.AlignmentFlag.AlignCenter, "Boss")


class RaidEngineDashboardPage(FoundryPage):
    pageRequested = Signal(str)
    sendTeamRequested = Signal()
    helpRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.comp_builder = None
        self.optimization = None
        self.coverage = None
        self.encounters = None
        self.performance = None
        self._syncing_context = False
        self._build_ui()

    def set_sources(self, *, comp_builder=None, optimization=None, coverage=None, encounters=None, performance=None) -> None:
        self.comp_builder = comp_builder
        self.optimization = optimization
        self.coverage = coverage
        self.encounters = encounters
        self.performance = performance
        self.refresh()

    @staticmethod
    def _context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Raid Engine Dashboard",
            subtitle="Track your active composition, readiness, optimization state, and encounter progress at a glance.",
            department="RAID ENGINE • DASHBOARD",
            icon="dashboard",
        )
        self.set_header(self.header)

        self.trial_combo = QComboBox()
        self.trial_combo.setMinimumWidth(170)
        self.trial_combo.addItems(("Dreadsail Reef", "Sunspire", "Cloudrest", "Rockgrove", "Lucent Citadel", "Sanity's Edge"))
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(("Veteran Hardmode", "Veteran", "Normal"))
        self.plan_combo = QComboBox()
        self.plan_combo.setMinimumWidth(260)
        self.plan_combo.addItem("Current Raid Composition")
        self.help_button = FoundryButton("? Help", role=ButtonRole.GHOST, compact=True)
        self.help_button.clicked.connect(lambda *_: self.helpRequested.emit())
        self.header.add_context_widget(self._context_field("TRIAL", self.trial_combo))
        self.header.add_context_widget(self._context_field("DIFFICULTY", self.difficulty_combo))
        self.header.add_context_widget(self._context_field("CURRENT TEAM / PLAN", self.plan_combo))
        self.header.add_context_widget(self.help_button)

        workspace = QWidget()
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(9)

        top = QHBoxLayout()
        top.setSpacing(9)

        self.composition_card = FoundryCard("Composition Ring", "dashboard")
        self.composition_ring = CompositionRingWidget()
        self.composition_card.addWidget(self.composition_ring)
        top.addWidget(self.composition_card, 42)

        self.active_card = FoundryCard("Active Composition", "team")
        self.active_table = QTableWidget(0, 4)
        self.active_table.setHorizontalHeaderLabels(("SLOT", "PLAYER", "CLASS", "STATUS"))
        self.active_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.active_table.verticalHeader().setVisible(False)
        self.active_table.horizontalHeader().setStretchLastSection(True)
        self.active_table.setMinimumHeight(340)
        self.active_card.addWidget(self.active_table)
        top.addWidget(self.active_card, 28)

        right = QVBoxLayout()
        right.setSpacing(9)
        self.optimization_card = FoundryCard("Planning Pulse", "chart")
        pulse = QHBoxLayout()
        self.readiness_ring = ReadinessRingWidget()
        pulse.addWidget(self.readiness_ring, 0, Qt.AlignmentFlag.AlignTop)
        self.optimization_metrics = QLabel()
        self.optimization_metrics.setWordWrap(True)
        pulse.addWidget(self.optimization_metrics, 1)
        self.optimization_card.addLayout(pulse)
        self.optimization_note = QLabel()
        self.optimization_note.setWordWrap(True)
        self.optimization_note.setProperty("pageSubtitle", True)
        self.optimization_card.addWidget(self.optimization_note)
        right.addWidget(self.optimization_card, 1)

        self.coverage_card = FoundryCard("Coverage Snapshot", "shield")
        self.coverage_scope_label = QLabel("Select saved builds in Team Optimization to check this team.")
        self.coverage_scope_label.setWordWrap(True)
        self.coverage_card.addWidget(self.coverage_scope_label)
        self.coverage_grid = QGridLayout()
        self.coverage_grid.setHorizontalSpacing(12)
        self.coverage_grid.setVerticalSpacing(4)
        self.coverage_card.addLayout(self.coverage_grid)
        self.send_coverage_button = FoundryButton("Send Selected Team to Coverage", role=ButtonRole.PRIMARY, compact=True)
        self.send_coverage_button.setToolTip("Check exactly the saved builds selected in Team Optimization; open slots stay open.")
        self.send_coverage_button.clicked.connect(self._send_team_to_coverage)
        self.coverage_card.addWidget(self.send_coverage_button)
        coverage_link = FoundryButton("Browse All Saved Builds →", role=ButtonRole.GHOST, compact=True)
        coverage_link.clicked.connect(self._browse_all_coverage)
        self.coverage_card.addWidget(coverage_link)
        right.addWidget(self.coverage_card, 1)
        top.addLayout(right, 30)
        root.addLayout(top, 6)

        bottom = QHBoxLayout()
        bottom.setSpacing(9)

        self.encounter_card = FoundryCard("Encounter Snapshot", "trial")
        self.encounter_title = QLabel("Current Encounter: No Encounter Selected")
        self.encounter_card.addWidget(self.encounter_title)
        encounter_row = QHBoxLayout()
        encounter_row.addWidget(EncounterMiniMap(), 1)
        self.timeline_label = QLabel(
            "0:00   Pull\n0:20   Portal Spawn\n0:45   Heavy Attack\n1:10   Orbs\n"
            "1:30   Portal Adds\n1:55   Chains\n2:10   Phase Transition\n4:20   Phase 3 Begins\n6:10   Execute"
        )
        encounter_row.addWidget(self.timeline_label, 1)
        self.encounter_card.addLayout(encounter_row)
        encounter_link = FoundryButton("View Encounter Details →", role=ButtonRole.GHOST, compact=True)
        encounter_link.clicked.connect(lambda *_: self.pageRequested.emit("console:1"))
        self.encounter_card.addWidget(encounter_link)
        bottom.addWidget(self.encounter_card, 34)

        self.performance_card = FoundryCard("Performance Signals", "capabilities")
        self.performance_summary = QLabel()
        self.performance_summary.setWordWrap(True)
        self.performance_card.addWidget(self.performance_summary)
        self.performance_card.addStretch(1)
        performance_link = FoundryButton("View Full Performance →", role=ButtonRole.GHOST, compact=True)
        performance_link.clicked.connect(lambda *_: self.pageRequested.emit("console:3"))
        self.performance_card.addWidget(performance_link)
        bottom.addWidget(self.performance_card, 30)

        self.next_actions_card = FoundryCard("Next Actions", "checklist").make_parchment()
        self.next_actions_label = QLabel()
        self.next_actions_label.setWordWrap(True)
        self.next_actions_card.addWidget(self.next_actions_label)
        self.next_actions_card.addStretch(1)
        bottom.addWidget(self.next_actions_card, 36)
        root.addLayout(bottom, 3)

        quick_card = FoundryCard("Quick Actions", "bolt")
        quick_row = QHBoxLayout()
        actions = (
            ("Open Comp Builder", "comp_builder"),
            ("Open Optimization", "console:6"),
            ("Open Coverage", "console:7"),
            ("Open Encounters", "console:1"),
            ("Open Performance", "console:3"),
        )
        for text, route in actions:
            button = FoundryButton(text, role=ButtonRole.SECONDARY, compact=True)
            button.clicked.connect(lambda *_args, target=route: self.pageRequested.emit(target))
            quick_row.addWidget(button, 1)
        send = FoundryButton("Send Team to Roster", role=ButtonRole.PRIMARY, compact=True)
        send.clicked.connect(lambda *_: self.sendTeamRequested.emit())
        quick_row.addWidget(send, 1)
        quick_card.addLayout(quick_row)
        root.addWidget(quick_card)

        self.add_workspace(workspace)
        self.status = FoundryStatusBar()
        self.set_status(self.status)

        self.trial_combo.currentTextChanged.connect(self._context_changed)
        self.difficulty_combo.currentTextChanged.connect(self._context_changed)

    def showEvent(self, event) -> None:  # noqa: N802
        self.refresh()
        super().showEvent(event)

    def _context_changed(self, *_args) -> None:
        if self._syncing_context:
            return
        difficulty = self.difficulty_combo.currentText()
        for page in (self.comp_builder, self.optimization):
            combo = getattr(page, "difficulty_combo", None)
            if isinstance(combo, QComboBox):
                index = combo.findText(difficulty)
                if index >= 0 and combo.currentIndex() != index:
                    combo.setCurrentIndex(index)

        trial = self.trial_combo.currentText()
        # Newer Comp Maker support may expose a trial selector directly. Older
        # builds remain goal-driven, so do not guess an achievement goal here.
        combo = getattr(self.comp_builder, "trial_combo", None)
        if isinstance(combo, QComboBox):
            index = combo.findText(trial)
            if index >= 0 and combo.currentIndex() != index:
                combo.setCurrentIndex(index)
        self.refresh()

    def _optimization_slots(self) -> tuple[RaidSlotSnapshot, ...]:
        page = self.optimization
        table = getattr(page, "team_table", None)
        if page is None or not isinstance(table, QTableWidget):
            return ()
        if hasattr(page, "team_tabs") and page.team_tabs.currentIndex() == 1:
            table = getattr(page, "team_b_table", table)

        slots: list[RaidSlotSnapshot] = []
        roster = getattr(getattr(page, "roster", None), "Members", [])
        for row in range(table.rowCount()):
            slot = _normalize_slot_name(_table_text(table, row, 0))
            if not slot:
                continue
            selector = table.cellWidget(row, 1)
            selection = selector.currentData() if isinstance(selector, QComboBox) else None
            if isinstance(selection, int) and 0 <= selection < len(roster):
                player, eso_class, build = _build_identity(roster[selection])
                slots.append(RaidSlotSnapshot(slot, player, eso_class, build, "SAVED"))
            elif isinstance(selection, str) and selection.startswith("recruitment:"):
                slots.append(RaidSlotSnapshot(slot, "Recruitment Needed", "Flexible", "Open requirement", "NEEDS BUILD"))
            else:
                slots.append(RaidSlotSnapshot(slot=slot))
        return tuple(slots)

    def _selected_team_members(self):
        """Only explicit saved-build selections, with their optimization slot."""
        page = self.optimization
        table = getattr(page, "team_table", None)
        if not isinstance(table, QTableWidget):
            return ()
        if hasattr(page, "team_tabs") and page.team_tabs.currentIndex() == 1:
            table = getattr(page, "team_b_table", table)
        roster = getattr(getattr(page, "roster", None), "Members", ())
        selected = []
        for row in range(table.rowCount()):
            slot = _normalize_slot_name(_table_text(table, row, 0))
            selector = table.cellWidget(row, 1)
            index = selector.currentData() if isinstance(selector, QComboBox) else None
            if slot in RAID_SLOTS and isinstance(index, int) and 0 <= index < len(roster):
                selected.append((slot, roster[index]))
        return tuple(selected)

    def _send_team_to_coverage(self, *_args) -> None:
        selected = self._selected_team_members()
        if self.coverage is None or not selected:
            self.status.warning("Select saved builds in Team Optimization before sending a team to Coverage.")
            return
        self.coverage.set_team_scope(self.plan_combo.currentText(), selected, total_slots=len(RAID_SLOTS))
        self.pageRequested.emit("console:7")

    def _browse_all_coverage(self, *_args) -> None:
        if self.coverage is not None:
            self.coverage.scope_combo.setCurrentIndex(self.coverage.scope_combo.findData("all"))
        self.pageRequested.emit("console:7")

    def _comp_slots(self) -> tuple[RaidSlotSnapshot, ...]:
        page = self.comp_builder
        table = getattr(page, "matrix_table", None)
        if page is None or not isinstance(table, QTableWidget):
            return tuple(RaidSlotSnapshot(slot=name) for name in RAID_SLOTS)
        slot_col = _table_column(table, ("SLOT",))
        class_col = _table_column(table, ("CLASS", "PREFERRED CLASS"))
        build_col = _table_column(table, ("ASSIGNED BUILD", "BUILD"))
        slots: list[RaidSlotSnapshot] = []
        for row in range(table.rowCount()):
            slot = _normalize_slot_name(_table_text(table, row, slot_col))
            if not slot:
                continue
            eso_class = _table_text(table, row, class_col)
            build = _table_text(table, row, build_col)
            status = "SAVED" if build and build.casefold() not in {"open", "—", "none"} else "OPEN"
            slots.append(RaidSlotSnapshot(slot, "", eso_class, build, status))
        by_name = {slot.slot: slot for slot in slots}
        return tuple(by_name.get(name, RaidSlotSnapshot(slot=name)) for name in RAID_SLOTS)

    def _slot_snapshot(self) -> tuple[RaidSlotSnapshot, ...]:
        optimization_slots = self._optimization_slots()
        if optimization_slots and any(slot.status != "OPEN" for slot in optimization_slots):
            by_name = {slot.slot: slot for slot in optimization_slots}
            return tuple(by_name.get(name, RaidSlotSnapshot(slot=name)) for name in RAID_SLOTS)
        return self._comp_slots()

    def _coverage_snapshot(self) -> CoverageSnapshot:
        selected = self._selected_team_members()
        if self.coverage is None or not selected:
            return CoverageSnapshot(tuple((name, "unverified") for name in COVERAGE_WATCH), 0, len(COVERAGE_WATCH))
        snapshot = self.coverage.snapshot_for_builds(tuple(build for _, build in selected))
        effects = tuple((name, snapshot.status.get(name, "unverified")) for name in COVERAGE_WATCH)
        return CoverageSnapshot(effects, sum(state == "available" for _, state in effects), len(effects))

    def _optimization_snapshot(self, slots: tuple[RaidSlotSnapshot, ...], coverage: CoverageSnapshot) -> OptimizationSnapshot:
        assigned = sum(1 for slot in slots if slot.status == "SAVED")
        analysis = getattr(self.optimization, "_optimization_current_canonical_analysis", None)
        saved_builds = int(getattr(analysis, "saved_build_count", assigned) or 0)
        gaps = int(getattr(analysis, "capability_gap_count", 0) or 0)
        build_swaps = 0
        prescription = getattr(self.optimization, "current_prescription", None)
        if prescription is not None:
            candidates = getattr(prescription, "assignments", ()) or ()
            build_swaps = sum(1 for candidate in candidates if _clean(getattr(candidate, "build_name", "")))
        readiness = _readiness_score(
            assigned=assigned,
            total_slots=len(RAID_SLOTS),
            covered=coverage.covered,
            total_coverage=max(1, coverage.total),
            capability_gaps=gaps,
        )
        return OptimizationSnapshot(assigned, saved_builds, coverage.covered, coverage.total, gaps, build_swaps, readiness)

    def _sync_context_labels(self) -> None:
        self._syncing_context = True
        try:
            difficulty = _clean(getattr(getattr(self.comp_builder, "difficulty_combo", None), "currentText", lambda: "")())
            if not difficulty:
                difficulty = _clean(getattr(getattr(self.optimization, "difficulty_combo", None), "currentText", lambda: "")())
            if difficulty:
                index = self.difficulty_combo.findText(difficulty)
                if index >= 0:
                    self.difficulty_combo.setCurrentIndex(index)

            template = getattr(self.comp_builder, "current_template", None)
            trial = _clean(getattr(template, "trial_name", ""))
            if not trial:
                trial = _clean(getattr(getattr(self.comp_builder, "trial_combo", None), "currentText", lambda: "")())
            if trial:
                index = self.trial_combo.findText(trial)
                if index < 0:
                    self.trial_combo.addItem(trial)
                    index = self.trial_combo.findText(trial)
                self.trial_combo.setCurrentIndex(index)

            plan = _clean(getattr(getattr(self.comp_builder, "plan_name_input", None), "text", lambda: "")())
            team_b = hasattr(self.optimization, "team_tabs") and self.optimization.team_tabs.currentIndex() == 1
            loaded = _clean(getattr(self.optimization, "_optimization_loaded_team_name_b" if team_b else "_optimization_loaded_team_name_a", ""))
            if self._selected_team_members():
                display = loaded or f"Team Optimization • Team {'B' if team_b else 'A'}"
            else:
                display = plan or "Current Raid Composition"
            self.plan_combo.clear()
            self.plan_combo.addItem(display)
        finally:
            self._syncing_context = False

    def _refresh_active_table(self, slots: tuple[RaidSlotSnapshot, ...]) -> None:
        self.active_table.setRowCount(len(slots))
        for row, slot in enumerate(slots):
            values = (slot.slot, slot.player or "—", slot.eso_class or "—", slot.status)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setData(Qt.ItemDataRole.UserRole, slot.status)
                self.active_table.setItem(row, column, item)
        self.active_table.resizeColumnsToContents()

    def _refresh_coverage(self, coverage: CoverageSnapshot) -> None:
        while self.coverage_grid.count():
            item = self.coverage_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        labels = {"available": "✓ Static source", "conditional": "◇ Conditional", "not_found": "? Not identified", "unverified": "? Unverified"}
        priority = {"available": 0, "conditional": 1, "not_found": 2, "unverified": 3}
        ranked = sorted(coverage.effects, key=lambda entry: priority.get(entry[1], 3))
        for row, (effect, evidence) in enumerate(ranked[:5]):
            name = QLabel(effect)
            state = QLabel(labels.get(evidence, "? Unverified"))
            state.setProperty("dashboardCoverageState", evidence)
            self.coverage_grid.addWidget(name, row, 0)
            self.coverage_grid.addWidget(state, row, 1)
        if len(ranked) > 5:
            self.coverage_grid.addWidget(QLabel(f"+ {len(ranked) - 5} more checks in Coverage"), 5, 0, 1, 2)

    def _refresh_encounter(self) -> None:
        title = "No Encounter Selected"
        for attr in ("boss_combo", "encounter_combo", "encounter_selector"):
            combo = getattr(self.encounters, attr, None)
            if isinstance(combo, QComboBox) and _clean(combo.currentText()):
                title = _clean(combo.currentText())
                break
        self.encounter_title.setText(f"Current Encounter: {title}")

    def _refresh_performance(self) -> None:
        # Performance has several support layers and may not have a loaded ESO Logs
        # report. Surface stable, available state without pretending a parse exists.
        page = self.performance
        member = "No report loaded"
        summary = "Open Performance to load a report and inspect HPS, uptime, debuffs, and top abilities."
        if page is not None:
            member_combo = getattr(page, "member_combo", None)
            if isinstance(member_combo, QComboBox) and _clean(member_combo.currentText()):
                member = _clean(member_combo.currentText())
            status = getattr(page, "status", None)
            label = getattr(status, "label", None)
            text = _clean(label.text() if isinstance(label, QLabel) else "")
            if text:
                summary = text
        self.performance_summary.setText(f"Latest Report: {member}\n\n{summary}")

    def _refresh_next_actions(self, slots: tuple[RaidSlotSnapshot, ...], coverage: CoverageSnapshot, optimization: OptimizationSnapshot) -> None:
        open_slots = [slot.slot for slot in slots if slot.status == "OPEN"]
        needs_build = [slot.slot for slot in slots if slot.status == "NEEDS BUILD"]
        missing = [name for name, state in coverage.effects if state == "not_found"]
        unknown = sum(state == "unverified" for _, state in coverage.effects)
        actions: list[str] = []
        if "Off Tank" in open_slots:
            actions.append("☐  Assign an Off Tank.")
        dd_open = sum(1 for name in open_slots if name.startswith("DD "))
        if dd_open:
            actions.append(f"☐  Fill DD roster ({dd_open} slot(s) open).")
        if needs_build:
            actions.append(f"☐  Finish builds for {', '.join(needs_build[:3])}{'…' if len(needs_build) > 3 else ''}.")
        if missing:
            actions.append(f"☐  Review sources not identified: {', '.join(missing[:3])}{'…' if len(missing) > 3 else ''}.")
        if unknown:
            actions.append(f"☐  Review evidence for {unknown} unverified effect(s).")
        if optimization.capability_gaps:
            actions.append(f"☐  Review {optimization.capability_gaps} capability-resolution gap(s).")
        actions.append("☐  Load a saved team or send the current team to Roster.")
        actions.append("☐  Run a test parse and review Performance when the team is ready.")
        self.next_actions_label.setText("\n\n".join(actions[:6]))

    def refresh(self) -> None:
        # Let source pages update their own canonical read models first.
        for page in (self.optimization, self.coverage):
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                try:
                    refresh()
                except (OSError, ValueError, AttributeError):
                    pass

        self._sync_context_labels()
        slots = self._slot_snapshot()
        selected = self._selected_team_members()
        self.send_coverage_button.setEnabled(bool(selected))
        if selected:
            self.coverage_scope_label.setText(
                f"Team Optimization: {len(selected)}/{len(RAID_SLOTS)} slots have saved builds. "
                "Check this selected team; open slots have no coverage evidence."
            )
        else:
            self.coverage_scope_label.setText(
                "No saved builds selected in Team Optimization. Select a build in its team slots to check team coverage."
            )
        coverage = self._coverage_snapshot()
        optimization = self._optimization_snapshot(slots, coverage)

        self.composition_ring.set_slots(slots)
        self._refresh_active_table(slots)
        self._refresh_coverage(coverage)
        self.readiness_ring.setValue(optimization.readiness)
        self.optimization_metrics.setText(
            f"Assigned Slots          {optimization.assigned} / 12\n"
            f"Saved Builds            {optimization.saved_builds}\n"
            f"Static Sources Found     {optimization.coverage_covered} / {max(optimization.coverage_total, 0)}\n"
            f"Capability Gaps          {optimization.capability_gaps}\n"
            f"Build Swaps Suggested    {optimization.build_swaps}"
        )
        if optimization.readiness >= 80:
            note = "Planning estimate only. Review assignments, mechanics and actual combat evidence before the pull."
        elif optimization.readiness >= 45:
            note = "Planning estimate only. Fill open slots and review unverified coverage next."
        else:
            note = "Planning estimate only. Fill open slots and review unverified coverage next."
        self.optimization_note.setText(note)
        self._refresh_encounter()
        self._refresh_performance()
        self._refresh_next_actions(slots, coverage, optimization)
        self.status.info(
            f"Raid Engine dashboard ready • {optimization.assigned}/12 assigned • "
            f"{optimization.coverage_covered}/{max(optimization.coverage_total, 0)} static sources identified."
        )
