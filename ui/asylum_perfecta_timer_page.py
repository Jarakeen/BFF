from __future__ import annotations

"""Asylum Sanctorium +2 Perfecta console timer.

This page is intentionally designed as an operational companion for console play:
large controls, manual event confirmation, and readable countdowns instead of an
editor-heavy desktop workflow.
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
from ui.ux_icons import set_button_icon


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
    """Timer art that keeps Foundry gold but mutes toward steel in Rylo."""

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

    def refresh_theme(self, rylo: bool) -> None:
        if self._rylo == rylo and self.pixmap() is not None and not self.pixmap().isNull():
            return
        self._rylo = rylo
        path = _artwork_path(self.kind)
        if path is None:
            self.clear()
            self.setText(self.kind.replace("_", " ").title())
            self.setProperty("pageSubtitle", True)
            return

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
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
            painter.fillRect(tinted.rect(), QColor(112, 125, 134, 100))
            painter.end()
            pixmap = tinted
        self.setPixmap(pixmap)


class EnrageTimeline(QWidget):
    """Full-width green-to-red enrage track with a moving current-time marker."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._remaining = float(MINI_ENRAGE_SECONDS)
        self._active = False
        self._rylo = False
        self.setMinimumHeight(48)
        self.setMaximumHeight(54)
        self.setToolTip("3:00 active · 1:30 health check · 0:30 execute · 0:00 enrage")

    def set_state(self, remaining: float, *, active: bool, rylo: bool) -> None:
        self._remaining = max(0.0, min(float(MINI_ENRAGE_SECONDS), float(remaining)))
        self._active = active
        self._rylo = rylo
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        left = 10.0
        right = max(left + 10.0, self.width() - 10.0)
        bar_top = 8.0
        bar_height = 10.0
        bar_rect = QRectF(left, bar_top, right - left, bar_height)

        if self._rylo:
            start, middle, execute, end = (
                QColor("#637C70"), QColor("#A4976D"), QColor("#9C6E4A"), QColor("#8D4F4F")
            )
            text_color = QColor("#B8BDC1")
            marker_color = QColor("#E0E0DE")
        else:
            start, middle, execute, end = (
                QColor("#3DAA66"), QColor("#D5B14C"), QColor("#D8873D"), QColor("#C34B42")
            )
            text_color = QColor("#C9B07A")
            marker_color = QColor("#F0E7D6")

        gradient = QLinearGradient(left, 0, right, 0)
        gradient.setColorAt(0.0, start)
        gradient.setColorAt(0.50, middle)
        gradient.setColorAt(0.84, execute)
        gradient.setColorAt(1.0, end)
        painter.setPen(QPen(QColor("#8A6B43" if not self._rylo else "#64686B"), 1.0))
        painter.setBrush(gradient)
        painter.drawRoundedRect(bar_rect, 5.0, 5.0)

        # Elapsed position runs left (spawn) to right (enrage).
        elapsed_ratio = 1.0 - (self._remaining / float(MINI_ENRAGE_SECONDS))
        marker_x = left + elapsed_ratio * (right - left)
        painter.setPen(QPen(marker_color, 2.0))
        painter.drawLine(int(marker_x), 4, int(marker_x), 23)

        if not self._active:
            painter.fillRect(bar_rect, QColor(7, 15, 17, 150))

        painter.setPen(text_color)
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        labels = (
            (0.0, "3:00\nSPAWN"),
            (0.50, "1:30\nCHECK"),
            (5.0 / 6.0, "0:30\nEXECUTE"),
            (1.0, "0:00\nENRAGE"),
        )
        for ratio, text in labels:
            x = left + ratio * (right - left)
            width = 58.0
            if ratio == 0.0:
                x = left
            elif ratio == 1.0:
                x = right - width
            else:
                x -= width / 2.0
            painter.drawText(
                QRectF(x, 23.0, width, 25.0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                text,
            )
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
        self._build_workspace()

        self._ticker = QTimer(self)
        self._ticker.setInterval(250)
        self._ticker.timeout.connect(self._tick)
        self._ticker.start()
        self._refresh()

    @staticmethod
    def _big_label(text: str = "--:--", size: int = 46) -> QLabel:
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
        button.setMinimumHeight(48)
        button.setProperty("primary", True)
        if icon:
            set_button_icon(button, icon, 19)
        return button

    def _art(self, kind: str, width: int, height: int) -> TimerArtwork:
        label = TimerArtwork(kind, width, height)
        self._artwork_labels.append(label)
        return label

    def _build_workspace(self) -> None:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        for column in range(12):
            grid.setColumnStretch(column, 1)

        # Hero timer mirrors the mockup: oversized hourglass, master clock,
        # deaths, and status in one broad card.
        run_card = FoundryCard("Perfecta Run Timer", "hourglass")
        run_card.setMinimumHeight(178)
        run_row = QHBoxLayout()
        run_row.setSpacing(14)
        run_row.addWidget(self._art("hourglass", 118, 132), 0, Qt.AlignmentFlag.AlignCenter)

        clock_box = QVBoxLayout()
        self.run_clock = self._big_label("15:00", 64)
        clock_box.addWidget(self.run_clock)
        remaining = QLabel("REMAINING  (15:00)")
        remaining.setAlignment(Qt.AlignmentFlag.AlignCenter)
        remaining.setProperty("timerAccent", True)
        clock_box.addWidget(remaining)
        run_row.addLayout(clock_box, 3)

        deaths_box = QVBoxLayout()
        deaths_box.addWidget(self._muted("DEATHS"))
        self.deaths_label = self._big_label("0", 38)
        deaths_box.addWidget(self.deaths_label)
        run_row.addLayout(deaths_box, 1)

        status_box = QVBoxLayout()
        status_box.addWidget(self._muted("STATUS"))
        self.run_status = self._big_label("READY", 22)
        status_box.addWidget(self.run_status)
        run_row.addLayout(status_box, 1)
        run_card.addLayout(run_row)
        grid.addWidget(run_card, 0, 0, 1, 8)

        quick_card = FoundryCard("Quick Actions", "stopwatch")
        quick = QGridLayout()
        self.start_button = self._large_button("Start Perfecta", "stopwatch")
        self.start_button.clicked.connect(self._start_or_pause)
        self.death_button = self._large_button("Add Death", "death-skull")
        self.death_button.clicked.connect(self._add_death)
        self.reset_button = self._large_button("Reset Encounter", "refresh")
        self.reset_button.clicked.connect(self._reset)
        self.kite_button = self._large_button("Kite Happened", "refresh")
        self.kite_button.clicked.connect(self._mark_kite)
        self.protector_button = self._large_button("Protector Died", "check-mark")
        self.protector_button.clicked.connect(self._mark_protector)
        quick.addWidget(self.start_button, 0, 0, 1, 2)
        quick.addWidget(self.death_button, 1, 0)
        quick.addWidget(self.reset_button, 1, 1)
        quick.addWidget(self.kite_button, 2, 0)
        quick.addWidget(self.protector_button, 2, 1)
        quick_card.addLayout(quick)
        grid.addWidget(quick_card, 0, 8, 1, 4)

        self.llothis_widgets = self._mini_card("Saint Llothis", "Llothis", "llothis")
        self.felms_widgets = self._mini_card("Saint Felms", "Felms", "felms")
        grid.addWidget(self.llothis_widgets["card"], 1, 0, 1, 6)
        grid.addWidget(self.felms_widgets["card"], 1, 6, 1, 6)

        olms_card = FoundryCard("Saint Olms", "boss")
        olms_card.setMinimumHeight(190)
        olms_row = QHBoxLayout()
        olms_row.setSpacing(10)
        olms_row.addWidget(self._art("olms", 145, 155), 0, Qt.AlignmentFlag.AlignCenter)
        olms_details = QVBoxLayout()
        self.olms_health = QLabel("100%")
        self.olms_health.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.olms_health.setProperty("timerClock", True)
        self.olms_health.setStyleSheet("font-size: 34px; font-weight: 700;")
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
        thresholds = self._muted("90%      75%      50%      25%")
        thresholds.setAlignment(Qt.AlignmentFlag.AlignCenter)
        olms_details.addWidget(thresholds)
        olms_row.addLayout(olms_details, 1)
        olms_card.addLayout(olms_row)
        grid.addWidget(olms_card, 2, 0, 1, 5)

        storm_card = FoundryCard("Storm the Heavens", "stopwatch")
        storm_box = QVBoxLayout()
        storm_box.addWidget(self._art("storm", 110, 100), 0, Qt.AlignmentFlag.AlignCenter)
        self.kite_clock = self._big_label("~00:34", 31)
        storm_box.addWidget(self.kite_clock)
        hint = self._muted("Predictive kite window · ~34 sec")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        storm_box.addWidget(hint)
        storm_card.addLayout(storm_box)
        grid.addWidget(storm_card, 2, 5, 1, 3)

        protector_card = FoundryCard("Protectors", "shield")
        protector_box = QVBoxLayout()
        protector_box.addWidget(self._art("protector", 110, 100), 0, Qt.AlignmentFlag.AlignCenter)
        self.protector_clock = self._big_label("~00:10", 31)
        protector_box.addWidget(self.protector_clock)
        hint = self._muted("Since last protector death · ~8–12 sec")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        protector_box.addWidget(hint)
        protector_card.addLayout(protector_box)
        grid.addWidget(protector_card, 2, 8, 1, 4)

        llothis_mechs = FoundryCard("Llothis Mechanics", "crossed-swords")
        llothis_mechs.addWidget(self._mechanic_row("Oppressive Bolts", "12+ sec · INTERRUPT"))
        llothis_mechs.addWidget(self._mechanic_row("Defiled Blast / Cone", "20–24 sec"))
        llothis_mechs.addWidget(self._mechanic_row("Teleport", "25–35 sec"))
        grid.addWidget(llothis_mechs, 3, 0, 1, 4)

        felms_mechs = FoundryCard("Felms Mechanics", "crossed-swords")
        felms_mechs.addWidget(self._mechanic_row("Teleport Strike / Jumps", "~20 sec"))
        felms_mechs.addWidget(self._mechanic_row("Targeting", "Furthest player"))
        felms_mechs.addWidget(self._mechanic_row("Mini Enrage", "3:00 active"))
        grid.addWidget(felms_mechs, 3, 4, 1, 4)

        general = FoundryCard("General Timers", "hourglass")
        general.addWidget(self._mechanic_row("Kite / Storm", "~34 sec"))
        general.addWidget(self._mechanic_row("Protector Spawn", "~8–12 sec"))
        general.addWidget(self._mechanic_row("Mini Respawn", "1:00"))
        general.addWidget(self._mechanic_row("Mini Enrage", "3:00"))
        general.addWidget(self._mechanic_row("Enrage Stack", "+1 every 0:20 · max 6"))
        grid.addWidget(general, 3, 8, 1, 4)

        notes = FoundryCard("Perfecta Notes", "feather").make_parchment()
        notes.addWidget(
            self._muted(
                "• Llothis first activation follows Olms' first jump.\n"
                "• Felms first activation follows Olms' second jump, around 75%.\n"
                "• Check mini health at 1:30 remaining; call execute at 0:30.\n"
                "• Deactivation starts a 1:00 respawn timer; at 0:15, prepare for the mini to return.\n"
                "• Perfecta target: 15:00 and no group deaths. Manual event buttons remain the source of truth."
            )
        )
        grid.addWidget(notes, 4, 0, 1, 12)

        self.add_workspace_layout(grid)

    def _mechanic_row(self, left_text: str, right_text: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 2, 2, 2)
        left = QLabel(left_text)
        left.setProperty("timerMechanicName", True)
        right = QLabel(right_text)
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right.setProperty("pageSubtitle", True)
        layout.addWidget(left, 1)
        layout.addWidget(right)
        return row

    def _mini_card(self, title: str, key: str, artwork_kind: str) -> dict[str, object]:
        card = FoundryCard(title, "boss")
        card.setMinimumHeight(255)
        outer = QHBoxLayout()
        outer.setSpacing(12)
        outer.addWidget(self._art(artwork_kind, 170, 190), 0, Qt.AlignmentFlag.AlignTop)

        center = QVBoxLayout()
        state = QLabel("WAITING")
        state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        state.setProperty("timerStateBadge", True)
        center.addWidget(state)

        clock = self._big_label("--:--", 48)
        center.addWidget(clock)
        caption = QLabel("Waiting for first activation")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption.setProperty("timerAccent", True)
        center.addWidget(caption)

        timeline = EnrageTimeline()
        center.addWidget(timeline)

        callout = QLabel("Waiting for first activation")
        callout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        callout.setWordWrap(True)
        callout.setProperty("timerCallout", True)
        center.addWidget(callout)

        actions = QHBoxLayout()
        active = self._large_button(f"Mark {key} Active", "stopwatch")
        inactive = self._large_button(f"Mark {key} Deactivated", "check-mark")
        if key == "Llothis":
            active.clicked.connect(lambda: self._set_mini_active("llothis"))
            inactive.clicked.connect(lambda: self._set_mini_inactive("llothis"))
        else:
            active.clicked.connect(lambda: self._set_mini_active("felms"))
            inactive.clicked.connect(lambda: self._set_mini_inactive("felms"))
        actions.addWidget(active)
        actions.addWidget(inactive)
        center.addLayout(actions)
        outer.addLayout(center, 2)

        events = QVBoxLayout()
        heading = QLabel("LAST / NEXT EVENTS")
        heading.setProperty("timerAccent", True)
        events.addWidget(heading)
        if key == "Llothis":
            entries = ("Bolts    12+ sec", "Cone     20–24", "Teleport 25–35")
        else:
            entries = ("Jumps    ~20 sec", "Target   Furthest", "Return   0:15 warn")
        for entry in entries:
            label = self._muted(entry)
            label.setMinimumWidth(116)
            events.addWidget(label)
        events.addStretch()
        outer.addLayout(events, 1)

        card.addLayout(outer)
        return {
            "card": card,
            "state": state,
            "clock": clock,
            "caption": caption,
            "timeline": timeline,
            "callout": callout,
            "active": active,
            "inactive": inactive,
        }

    def _is_rylo(self) -> bool:
        app = QApplication.instance()
        return bool(app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO)

    def _apply_visual_theme(self) -> None:
        rylo = self._is_rylo()
        if self._rylo_state == rylo:
            return
        self._rylo_state = rylo

        if rylo:
            accent = "#B88A3C"
            clock = "#E0E0DE"
            callout = "#C8C6C1"
            state_border = "#676B70"
        else:
            accent = "#C8A46A"
            clock = "#E5ECEB"
            callout = "#D8D0C0"
            state_border = "#8A6F3D"

        self.setStyleSheet(
            f"""
            QWidget#asylumPerfectaTimerPage QLabel[timerAccent=\"true\"] {{
                color: {accent}; font-weight: 700; letter-spacing: 1px;
            }}
            QWidget#asylumPerfectaTimerPage QLabel[timerClock=\"true\"] {{
                color: {clock};
            }}
            QWidget#asylumPerfectaTimerPage QLabel[timerCallout=\"true\"] {{
                color: {callout}; font-size: 16px; font-weight: 600;
            }}
            QWidget#asylumPerfectaTimerPage QLabel[timerStateBadge=\"true\"] {{
                border: 1px solid {state_border}; border-radius: 4px;
                padding: 5px 12px; font-size: 17px; font-weight: 700;
            }}
            QWidget#asylumPerfectaTimerPage QLabel[timerMechanicName=\"true\"] {{
                font-weight: 600;
            }}
            """
        )
        for artwork in self._artwork_labels:
            artwork.refresh_theme(rylo)

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

    def _refresh_mini(self, mini, widgets: dict[str, object]) -> None:
        state_label: QLabel = widgets["state"]
        clock: QLabel = widgets["clock"]
        caption: QLabel = widgets["caption"]
        timeline: EnrageTimeline = widgets["timeline"]
        callout: QLabel = widgets["callout"]
        rylo = bool(self._rylo_state)

        state_label.setText(mini.state.value.upper())
        callout.setText(mini.callout)

        if mini.state == MiniState.WAITING:
            clock.setText("--:--")
            caption.setText("WAITING FOR FIRST ACTIVATION")
            timeline.set_state(MINI_ENRAGE_SECONDS, active=False, rylo=rylo)
            self._set_state_badge(state_label, "waiting")
            return

        if mini.state == MiniState.INACTIVE:
            remaining = mini.respawn_remaining or 0.0
            clock.setText(format_clock(remaining))
            caption.setText(f"UNTIL RESPAWN ({format_clock(MINI_RESPAWN_SECONDS)})")
            timeline.set_state(MINI_ENRAGE_SECONDS, active=False, rylo=rylo)
            self._set_state_badge(state_label, "inactive")
            return

        remaining = mini.enrage_remaining or 0.0
        clock.setText(format_clock(remaining))
        caption.setText("TO ENRAGE (03:00)" if mini.state == MiniState.ACTIVE else "ENRAGED")
        timeline.set_state(remaining, active=True, rylo=rylo)
        if mini.state == MiniState.ENRAGED:
            self._set_state_badge(state_label, "enraged")
        elif remaining <= 30:
            self._set_state_badge(state_label, "danger")
        else:
            self._set_state_badge(state_label, "active")

    def _set_state_badge(self, label: QLabel, state: str) -> None:
        rylo = self._is_rylo()
        if rylo:
            palette = {
                "waiting": ("#1A1C1D", "#8A8F93", "#60666A"),
                "inactive": ("#2A231C", "#C1A168", "#755D3B"),
                "active": ("#1C2823", "#AFC7B8", "#637C70"),
                "danger": ("#30231B", "#C9A175", "#9C6E4A"),
                "enraged": ("#301D1D", "#D0A0A0", "#8D4F4F"),
            }
        else:
            palette = {
                "waiting": ("#0B1719", "#AAB2AE", "#4F6565"),
                "inactive": ("#2B2215", "#E0BD79", "#8A6A35"),
                "active": ("#143826", "#D8F1E1", "#2F9A5C"),
                "danger": ("#432716", "#FFD39C", "#D17A32"),
                "enraged": ("#481D1A", "#FFD0C9", "#B8483F"),
            }
        bg, fg, border = palette[state]
        label.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border: 1px solid {border}; "
            "border-radius: 4px; padding: 5px 12px; font-size: 17px; font-weight: 700;"
        )

    def _refresh(self) -> None:
        self._apply_visual_theme()
        self.run_clock.setText(format_clock(self.model.perfecta_remaining))
        self.deaths_label.setText(str(self.model.deaths))
        self.run_status.setText(self.model.perfecta_status)
        self.start_button.setText("Pause Perfecta" if self.model.running else "Start Perfecta")
        set_button_icon(self.start_button, "stopwatch", 19)

        self._refresh_mini(self.model.llothis, self.llothis_widgets)
        self._refresh_mini(self.model.felms, self.felms_widgets)

        self.olms_health.setText(f"{self.model.olms_health_percent}%")
        next_jump = self.model.next_olms_jump
        self.olms_next_jump.setText(
            f"NEXT JUMP: {next_jump}%" if next_jump is not None else "EXECUTE · NO FURTHER HEALTH JUMP"
        )
        self.kite_clock.setText(f"~{format_clock(self.model.kite_window_seconds)}")
        self.protector_clock.setText(f"~{format_clock(self.model.protector_window_seconds)}")

        failed = self.model.perfecta_status.startswith("FAILED")
        failed_color = "#A96666" if self._is_rylo() else "#D96A5B"
        good_color = "#AEB3B7" if self._is_rylo() else "#76B6B0"
        self.run_status.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {failed_color if failed else good_color};"
        )

    def refresh_context(self) -> None:
        """Navigation/theme hook kept for future encounter-driven timer profiles."""
        self._rylo_state = None
        self._refresh()
