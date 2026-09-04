from __future__ import annotations

"""Asylum Sanctorium +2 Perfecta console timer.

Compact, large-control raid companion intended to fit in the normal BFF window
without vertical scrolling during play.
"""

import time

from PySide6.QtCore import QTimer, Qt, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_resource_path
from services.accessibility_preferences import VISUAL_THEME_RYLO
from services.asylum_sanctorium_timer import (
    AsylumPerfectaTimer,
    MINI_ENRAGE_SECONDS,
    MINI_RESPAWN_SECONDS,
    MiniState,
    format_clock,
)
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.foundry_page import FoundryPage
from ui.ux_icons import icon as themed_icon, set_button_icon


_ARTWORK_CANDIDATES = {
    "llothis": (
        "gilded_gothic_saint_helm.png",
        "llothis.png",
        "saint_llothis.png",
    ),
    "felms": (
        "molten_eyed_gothic_dreadlord_helm.png",
        "felms.png",
        "saint_felms.png",
    ),
    "olms": (
        "saint_olms_golden_eyed_war_machine.png",
        "olms.png",
        "saint_olms.png",
    ),
    "storm": (
        "aqua_storm_vortex_emblem.png",
        "storm_of_the_heavens.png",
        "storm.png",
    ),
    "protector": (
        "ornate_bronze_guardian_helmet_emblem.png",
        "protector_helmet.png",
        "protector.png",
        "protectors.png",
    ),
    "hourglass": (
        "ornate_antique_golden_hourglass.png",
        "hourglass.png",
    ),
}


def _artwork_path(kind: str):
    for filename in _ARTWORK_CANDIDATES.get(kind, ()):
        path = get_resource_path("assets", "timers", "vas2", filename)
        if path.exists():
            return path
    return None


class TimerArtwork(QLabel):
    """Compact timer art with a reliable semantic-icon fallback."""

    _FALLBACK_ICONS = {
        "llothis": "boss",
        "felms": "boss",
        "olms": "boss",
        "storm": "stopwatch",
        "protector": "shield",
        "hourglass": "hourglass",
    }

    def __init__(self, kind: str, width: int, height: int, parent=None):
        super().__init__(parent)
        self.kind = kind
        self._target_width = width
        self._target_height = height
        self._rylo = False
        self.setFixedSize(width, height)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(False)
        self.refresh_theme(False)

    def _fallback(self) -> None:
        self.clear()
        icon = themed_icon(self._FALLBACK_ICONS.get(self.kind, "boss"))
        if not icon.isNull():
            side = max(24, min(self._target_width, self._target_height) - 8)
            self.setPixmap(icon.pixmap(side, side))
            return
        self.setText(self.kind.replace("_", " ").title())
        self.setProperty("pageSubtitle", True)

    def refresh_theme(self, rylo: bool) -> None:
        self._rylo = rylo
        path = _artwork_path(self.kind)
        if path is None:
            self._fallback()
            return

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._fallback()
            return

        pixmap = pixmap.scaled(
            self._target_width,
            self._target_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if rylo:
            tinted = QPixmap(pixmap.size())
            tinted.fill(Qt.GlobalColor.transparent)
            painter = QPainter(tinted)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            painter.fillRect(tinted.rect(), QColor(112, 125, 134, 92))
            painter.end()
            pixmap = tinted
        self.setPixmap(pixmap)


class EnrageBar(QWidget):
    """Short, theme-aware green-to-red enrage bar with a moving marker."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._remaining = float(MINI_ENRAGE_SECONDS)
        self._active = False
        self._rylo = False
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setToolTip("3:00 spawn · 1:30 health check · 0:30 execute · 0:00 enrage")

    def set_state(self, remaining: float, *, active: bool, rylo: bool) -> None:
        self._remaining = max(0.0, min(float(MINI_ENRAGE_SECONDS), float(remaining)))
        self._active = active
        self._rylo = rylo
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        left = 4.0
        right = max(left + 8.0, self.width() - 4.0)
        rect = QRectF(left, 6.0, right - left, 9.0)

        if self._rylo:
            colors = ("#637C70", "#A4976D", "#9C6E4A", "#8D4F4F")
            marker = QColor("#E0E0DE")
            border = QColor("#64686B")
        else:
            colors = ("#3DAA66", "#D5B14C", "#D8873D", "#C34B42")
            marker = QColor("#F0E7D6")
            border = QColor("#8A6B43")

        gradient = QLinearGradient(left, 0, right, 0)
        gradient.setColorAt(0.0, QColor(colors[0]))
        gradient.setColorAt(0.50, QColor(colors[1]))
        gradient.setColorAt(5.0 / 6.0, QColor(colors[2]))
        gradient.setColorAt(1.0, QColor(colors[3]))
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 4.0, 4.0)

        elapsed_ratio = 1.0 - (self._remaining / float(MINI_ENRAGE_SECONDS))
        marker_x = left + elapsed_ratio * (right - left)
        painter.setPen(QPen(marker, 2.0))
        painter.drawLine(int(marker_x), 2, int(marker_x), 19)

        if not self._active:
            painter.fillRect(rect, QColor(7, 15, 17, 145))
        painter.end()


class AsylumPerfectaTimerPage(FoundryPage):
    """Large-button raid-lead console for Veteran Asylum Sanctorium +2."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("asylumPerfectaTimerPage")
        self.model = AsylumPerfectaTimer()
        self._last_tick = time.monotonic()
        self._rylo_state: bool | None = None
        self._artwork_labels: list[TimerArtwork] = []

        self.set_header(
            FoundryHeader(
                "Asylum Sanctorium · Perfecta Mode",
                "Console-mode vAS+2 raid timer for minis, Olms thresholds, kite, and protectors.",
                "Raid Engine • Timers",
                icon="stopwatch",
            )
        )
        self.workspace_layout.setSpacing(5)
        self._build_workspace()

        self._ticker = QTimer(self)
        self._ticker.setInterval(250)
        self._ticker.timeout.connect(self._tick)
        self._ticker.start()
        self._refresh()

    @staticmethod
    def _big_label(text: str = "--:--", size: int = 40) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setProperty("timerClock", True)
        label.setStyleSheet(f"font-size: {size}px; font-weight: 700;")
        return label

    @staticmethod
    def _muted(text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setProperty("pageSubtitle", True)
        return label

    @staticmethod
    def _large_button(text: str, icon: str = "") -> QPushButton:
        button = QPushButton(text)
        button.setMinimumHeight(54)
        button.setMinimumWidth(150)
        button.setProperty("primary", True)
        if icon:
            set_button_icon(button, icon, 20)
        return button

    def _art(self, kind: str, width: int, height: int) -> TimerArtwork:
        label = TimerArtwork(kind, width, height)
        self._artwork_labels.append(label)
        return label

    @staticmethod
    def _milestone_label(top: str, bottom: str) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        a = QLabel(top)
        b = QLabel(bottom)
        for label in (a, b):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setProperty("timerMilestone", True)
        layout.addWidget(a)
        layout.addWidget(b)
        return box

    def _build_workspace(self) -> None:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        for column in range(12):
            grid.setColumnStretch(column, 1)

        run_card = FoundryCard("Perfecta Run Timer", "hourglass")
        run_card.setMinimumHeight(122)
        run_card.setMaximumHeight(142)
        run_row = QHBoxLayout()
        run_row.setSpacing(10)
        run_row.addWidget(self._art("hourglass", 78, 92), 0, Qt.AlignmentFlag.AlignCenter)

        clock_box = QVBoxLayout()
        clock_box.setSpacing(0)
        self.run_clock = self._big_label("15:00", 54)
        clock_box.addWidget(self.run_clock)
        remaining = QLabel("REMAINING  (15:00)")
        remaining.setAlignment(Qt.AlignmentFlag.AlignCenter)
        remaining.setProperty("timerAccent", True)
        clock_box.addWidget(remaining)
        run_row.addLayout(clock_box, 3)

        deaths_box = QVBoxLayout()
        deaths_box.setSpacing(0)
        deaths_box.addWidget(self._muted("DEATHS"))
        self.deaths_label = self._big_label("0", 32)
        deaths_box.addWidget(self.deaths_label)
        run_row.addLayout(deaths_box, 1)

        status_box = QVBoxLayout()
        status_box.setSpacing(0)
        status_box.addWidget(self._muted("STATUS"))
        self.run_status = self._big_label("READY", 18)
        status_box.addWidget(self.run_status)
        run_row.addLayout(status_box, 1)
        run_card.addLayout(run_row)
        grid.addWidget(run_card, 0, 0, 1, 8)

        quick_card = FoundryCard("Quick Actions", "stopwatch")
        quick_card.setMinimumHeight(122)
        quick_card.setMaximumHeight(142)
        quick = QGridLayout()
        quick.setSpacing(5)
        self.start_button = self._large_button("Start Perfecta", "stopwatch")
        self.start_button.clicked.connect(self._start_or_pause)
        self.death_button = self._large_button("Add Death", "death-skull")
        self.death_button.clicked.connect(self._add_death)
        self.reset_button = self._large_button("Reset Encounter", "refresh")
        self.reset_button.clicked.connect(self._reset)
        quick.addWidget(self.start_button, 0, 0, 1, 2)
        quick.addWidget(self.death_button, 1, 0)
        quick.addWidget(self.reset_button, 1, 1)
        quick_card.addLayout(quick)
        grid.addWidget(quick_card, 0, 8, 1, 4)

        self.llothis_widgets = self._mini_card("Saint Llothis", "Llothis", "llothis")
        self.felms_widgets = self._mini_card("Saint Felms", "Felms", "felms")
        grid.addWidget(self.llothis_widgets["card"], 1, 0, 1, 6)
        grid.addWidget(self.felms_widgets["card"], 1, 6, 1, 6)

        olms_card = FoundryCard("Saint Olms", "boss")
        olms_card.setMaximumHeight(186)
        olms_row = QHBoxLayout()
        olms_row.setSpacing(8)
        olms_row.addWidget(self._art("olms", 88, 104), 0, Qt.AlignmentFlag.AlignCenter)
        olms_details = QVBoxLayout()
        olms_details.setSpacing(2)
        self.olms_health = QLabel("100%")
        self.olms_health.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.olms_health.setProperty("timerClock", True)
        self.olms_health.setStyleSheet("font-size: 28px; font-weight: 700;")
        olms_details.addWidget(self.olms_health)
        self.olms_slider = QSlider(Qt.Orientation.Horizontal)
        self.olms_slider.setRange(0, 100)
        self.olms_slider.setValue(100)
        self.olms_slider.valueChanged.connect(self._olms_health_changed)
        olms_details.addWidget(self.olms_slider)
        self.olms_next_jump = QLabel("NEXT JUMP: 90%")
        self.olms_next_jump.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.olms_next_jump.setProperty("timerAccent", True)
        olms_details.addWidget(self.olms_next_jump)
        thresholds = self._muted("90%   ·   75%   ·   50%   ·   25%")
        thresholds.setAlignment(Qt.AlignmentFlag.AlignCenter)
        olms_details.addWidget(thresholds)
        olms_row.addLayout(olms_details, 1)
        olms_card.addLayout(olms_row)
        grid.addWidget(olms_card, 2, 0, 1, 4)

        storm_card = FoundryCard("Storm the Heavens", "stopwatch")
        storm_card.setMaximumHeight(186)
        storm_box = QVBoxLayout()
        storm_box.setSpacing(1)
        storm_box.addWidget(self._art("storm", 68, 68), 0, Qt.AlignmentFlag.AlignCenter)
        self.kite_clock = self._big_label("~00:34", 27)
        storm_box.addWidget(self.kite_clock)
        self.kite_button = self._large_button("Kite Happened", "refresh")
        self.kite_button.clicked.connect(self._mark_kite)
        storm_box.addWidget(self.kite_button)
        storm_card.addLayout(storm_box)
        grid.addWidget(storm_card, 2, 4, 1, 4)

        protector_card = FoundryCard("Protectors", "shield")
        protector_card.setMaximumHeight(186)
        protector_box = QVBoxLayout()
        protector_box.setSpacing(1)
        protector_box.addWidget(self._art("protector", 68, 68), 0, Qt.AlignmentFlag.AlignCenter)
        self.protector_clock = self._big_label("~00:10", 27)
        protector_box.addWidget(self.protector_clock)
        self.protector_button = self._large_button("Protector Died", "check-mark")
        self.protector_button.clicked.connect(self._mark_protector)
        protector_box.addWidget(self.protector_button)
        protector_card.addLayout(protector_box)
        grid.addWidget(protector_card, 2, 8, 1, 4)

        mechanics = FoundryCard("Mechanic Reference", "crossed-swords")
        mechanics.setMaximumHeight(108)
        mech_row = QHBoxLayout()
        mech_row.setSpacing(16)
        ll = self._muted("LLOTHIS  ·  Bolts 12+ sec  ·  Cone 20–24  ·  Teleport 25–35")
        fe = self._muted("FELMS  ·  Jump cycle ~20 sec  ·  Targets furthest player")
        gen = self._muted("MINIS  ·  Enrage 3:00  ·  Respawn 1:00  ·  stacks +20 sec")
        mech_row.addWidget(ll, 2)
        mech_row.addWidget(fe, 2)
        mech_row.addWidget(gen, 2)
        mechanics.addLayout(mech_row)
        grid.addWidget(mechanics, 3, 0, 1, 12)

        self.add_workspace_layout(grid)

    def _mini_card(self, title: str, key: str, art_kind: str) -> dict[str, object]:
        card = FoundryCard(title, "boss")
        card.setMinimumHeight(232)
        card.setMaximumHeight(252)

        root = QHBoxLayout()
        root.setSpacing(10)
        root.addWidget(self._art(art_kind, 108, 128), 0, Qt.AlignmentFlag.AlignTop)

        center = QVBoxLayout()
        center.setSpacing(2)
        state = QLabel("WAITING")
        state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        state.setStyleSheet("font-size: 18px; font-weight: 700;")
        center.addWidget(state)

        clock = self._big_label("--:--", 36)
        center.addWidget(clock)
        caption = QLabel("WAITING FOR FIRST ACTIVATION")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption.setProperty("timerAccent", True)
        center.addWidget(caption)

        bar = EnrageBar()
        center.addWidget(bar)

        milestones = QHBoxLayout()
        milestones.setContentsMargins(0, 0, 0, 0)
        milestones.setSpacing(0)
        milestones.addWidget(self._milestone_label("3:00", "SPAWN"), 1)
        milestones.addWidget(self._milestone_label("1:30", "CHECK"), 1)
        milestones.addWidget(self._milestone_label("0:30", "EXECUTE"), 1)
        milestones.addWidget(self._milestone_label("0:00", "ENRAGE"), 1)
        center.addLayout(milestones)

        callout = QLabel("Waiting for first activation")
        callout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        callout.setWordWrap(False)
        callout.setStyleSheet("font-size: 15px; font-weight: 600;")
        center.addWidget(callout)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        active = self._large_button(f"Mark {key} Active", "stopwatch")
        inactive = self._large_button(f"Mark {key} Deactivated", "check-mark")
        if key == "Llothis":
            active.clicked.connect(lambda: self._set_mini_active("llothis"))
            inactive.clicked.connect(lambda: self._set_mini_inactive("llothis"))
        else:
            active.clicked.connect(lambda: self._set_mini_active("felms"))
            inactive.clicked.connect(lambda: self._set_mini_inactive("felms"))
        actions.addWidget(active, 1)
        actions.addWidget(inactive, 1)
        center.addLayout(actions)
        root.addLayout(center, 1)

        side = QVBoxLayout()
        side.setSpacing(4)
        heading = QLabel("LAST / NEXT EVENTS")
        heading.setProperty("timerAccent", True)
        side.addWidget(heading)
        if key == "Llothis":
            side.addWidget(self._muted("Bolts     12+ sec"))
            side.addWidget(self._muted("Cone      20–24"))
            side.addWidget(self._muted("Teleport  25–35"))
        else:
            side.addWidget(self._muted("Jumps     ~20 sec"))
            side.addWidget(self._muted("Target    Furthest"))
            side.addWidget(self._muted("Return    0:15 warn"))
        side.addStretch(1)
        root.addLayout(side)

        card.addLayout(root)
        return {
            "card": card,
            "state": state,
            "clock": clock,
            "caption": caption,
            "bar": bar,
            "callout": callout,
            "active": active,
            "inactive": inactive,
        }

    def _is_rylo(self) -> bool:
        app = QApplication.instance()
        return bool(app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO)

    def _refresh_theme(self) -> bool:
        rylo = self._is_rylo()
        if rylo != self._rylo_state:
            self._rylo_state = rylo
            for art in self._artwork_labels:
                art.refresh_theme(rylo)
        return rylo

    def _tick(self) -> None:
        now = time.monotonic()
        delta = max(0.0, min(1.0, now - self._last_tick))
        self._last_tick = now
        self.model.advance(delta)
        self._refresh()

    def _start_or_pause(self) -> None:
        if self.model.running:
            self.model.pause()
        else:
            self.model.start()
            self._last_tick = time.monotonic()
        self._refresh()

    def _add_death(self) -> None:
        self.model.add_death()
        self._refresh()

    def _reset(self) -> None:
        self.model.reset()
        self.olms_slider.setValue(100)
        self._last_tick = time.monotonic()
        self._refresh()

    def _set_mini_active(self, name: str) -> None:
        getattr(self.model, name).mark_active()
        if not self.model.running:
            self.model.start()
            self._last_tick = time.monotonic()
        self._refresh()

    def _set_mini_inactive(self, name: str) -> None:
        getattr(self.model, name).mark_inactive()
        self._refresh()

    def _mark_kite(self) -> None:
        self.model.mark_kite()
        self._refresh()

    def _mark_protector(self) -> None:
        self.model.mark_protector_death()
        self._refresh()

    def _olms_health_changed(self, value: int) -> None:
        self.model.olms_health_percent = int(value)
        self._refresh()

    def _refresh_mini(self, mini, widgets: dict[str, object], rylo: bool) -> None:
        state_label: QLabel = widgets["state"]
        clock: QLabel = widgets["clock"]
        caption: QLabel = widgets["caption"]
        bar: EnrageBar = widgets["bar"]
        callout: QLabel = widgets["callout"]

        state_label.setText(mini.state.value.upper())
        callout.setText(mini.callout)

        if mini.state == MiniState.WAITING:
            clock.setText("--:--")
            caption.setText("WAITING FOR FIRST ACTIVATION")
            bar.set_state(MINI_ENRAGE_SECONDS, active=False, rylo=rylo)
            state_label.setStyleSheet("font-size: 18px; font-weight: 700;")
            return

        if mini.state == MiniState.INACTIVE:
            remaining = mini.respawn_remaining or 0.0
            clock.setText(format_clock(remaining))
            caption.setText(f"UNTIL RESPAWN  ({format_clock(MINI_RESPAWN_SECONDS)})")
            bar.set_state(MINI_ENRAGE_SECONDS, active=False, rylo=rylo)
            color = "#A4976D" if rylo else "#C8A46A"
            state_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {color};")
            return

        remaining = mini.enrage_remaining or 0.0
        clock.setText(format_clock(remaining))
        caption.setText("TO ENRAGE  (03:00)" if mini.state == MiniState.ACTIVE else "ENRAGED")
        bar.set_state(remaining, active=True, rylo=rylo)
        if mini.state == MiniState.ENRAGED:
            color = "#8D4F4F" if rylo else "#D96A5B"
        elif remaining <= 30:
            color = "#9C6E4A" if rylo else "#E0A24C"
        else:
            color = "#637C70" if rylo else "#76B68B"
        state_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {color};")

    def _refresh(self) -> None:
        rylo = self._refresh_theme()
        self.run_clock.setText(format_clock(self.model.perfecta_remaining))
        self.deaths_label.setText(str(self.model.deaths))
        self.run_status.setText(self.model.perfecta_status)
        self.start_button.setText("Pause Perfecta" if self.model.running else "Start Perfecta")
        set_button_icon(self.start_button, "stopwatch", 20)

        self._refresh_mini(self.model.llothis, self.llothis_widgets, rylo)
        self._refresh_mini(self.model.felms, self.felms_widgets, rylo)

        self.olms_health.setText(f"{self.model.olms_health_percent}%")
        next_jump = self.model.next_olms_jump
        self.olms_next_jump.setText(
            f"NEXT JUMP: {next_jump}%" if next_jump is not None else "EXECUTE · NO FURTHER JUMP"
        )
        self.kite_clock.setText(f"~{format_clock(self.model.kite_window_seconds)}")
        self.protector_clock.setText(f"~{format_clock(self.model.protector_window_seconds)}")

        failed = self.model.perfecta_status.startswith("FAILED")
        if failed:
            color = "#8D4F4F" if rylo else "#D96A5B"
        else:
            color = "#AEB3B7" if rylo else "#76B6B0"
        self.run_status.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {color};")

    def refresh_context(self) -> None:
        self._refresh()
