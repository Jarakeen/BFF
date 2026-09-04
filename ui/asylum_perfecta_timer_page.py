from __future__ import annotations

"""Asylum Sanctorium +2 Perfecta console timer.

This page is intentionally designed as an operational companion for console play:
large controls, manual event confirmation, and readable countdowns instead of an
editor-heavy desktop workflow.
"""

import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from services.asylum_sanctorium_timer import (
    AsylumPerfectaTimer,
    KITE_INTERVAL_SECONDS,
    MINI_ENRAGE_SECONDS,
    MINI_RESPAWN_SECONDS,
    MiniState,
    format_clock,
)
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.foundry_page import FoundryPage
from ui.ux_icons import set_button_icon


class AsylumPerfectaTimerPage(FoundryPage):
    """Large-button raid-lead console for Veteran Asylum Sanctorium +2."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = AsylumPerfectaTimer()
        self._last_tick = time.monotonic()

        self.set_header(
            FoundryHeader(
                "Asylum Sanctorium · Perfecta Mode",
                "Large-button vAS+2 raid timer for minis, Olms thresholds, kite, and protectors.",
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

    def _build_workspace(self) -> None:
        top = QGridLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setHorizontalSpacing(8)
        top.setVerticalSpacing(8)

        run_card = FoundryCard("Perfecta Run Timer", "hourglass")
        run_row = QHBoxLayout()
        self.run_clock = self._big_label("15:00", 58)
        run_row.addWidget(self.run_clock, 2)

        deaths_box = QVBoxLayout()
        deaths_box.addWidget(self._muted("DEATHS"))
        self.deaths_label = self._big_label("0", 34)
        deaths_box.addWidget(self.deaths_label)
        run_row.addLayout(deaths_box, 1)

        status_box = QVBoxLayout()
        status_box.addWidget(self._muted("STATUS"))
        self.run_status = self._big_label("READY", 22)
        status_box.addWidget(self.run_status)
        run_row.addLayout(status_box, 1)
        run_card.addLayout(run_row)

        run_actions = QHBoxLayout()
        self.start_button = self._large_button("Start Perfecta", "stopwatch")
        self.start_button.clicked.connect(self._start_or_pause)
        self.death_button = self._large_button("Add Death", "death-skull")
        self.death_button.clicked.connect(self._add_death)
        self.reset_button = self._large_button("Reset Encounter", "refresh")
        self.reset_button.clicked.connect(self._reset)
        run_actions.addWidget(self.start_button)
        run_actions.addWidget(self.death_button)
        run_actions.addWidget(self.reset_button)
        run_card.addLayout(run_actions)
        top.addWidget(run_card, 0, 0, 1, 2)

        self.llothis_widgets = self._mini_card("Saint Llothis", "Llothis")
        self.felms_widgets = self._mini_card("Saint Felms", "Felms")
        top.addWidget(self.llothis_widgets["card"], 1, 0)
        top.addWidget(self.felms_widgets["card"], 1, 1)

        olms_card = FoundryCard("Saint Olms", "boss")
        self.olms_health = QLabel("100%")
        self.olms_health.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.olms_health.setStyleSheet("font-size: 30px; font-weight: 700;")
        olms_card.addWidget(self.olms_health)
        self.olms_slider = QSlider(Qt.Orientation.Horizontal)
        self.olms_slider.setRange(0, 100)
        self.olms_slider.setValue(100)
        self.olms_slider.valueChanged.connect(self._olms_health_changed)
        olms_card.addWidget(self.olms_slider)
        self.olms_next_jump = self._muted("Next jump: 90%")
        self.olms_next_jump.setAlignment(Qt.AlignmentFlag.AlignCenter)
        olms_card.addWidget(self.olms_next_jump)
        olms_card.addWidget(self._muted("Operational thresholds: 90% · 75% · 50% · 25%"))
        top.addWidget(olms_card, 2, 0)

        cadence_card = FoundryCard("Encounter Windows", "stopwatch")
        cadence_grid = QGridLayout()
        cadence_grid.addWidget(self._muted("Storm the Heavens / Kite"), 0, 0)
        self.kite_clock = self._big_label("~00:34", 28)
        cadence_grid.addWidget(self.kite_clock, 0, 1)
        self.kite_button = self._large_button("Kite Happened", "refresh")
        self.kite_button.clicked.connect(self._mark_kite)
        cadence_grid.addWidget(self.kite_button, 0, 2)

        cadence_grid.addWidget(self._muted("Protector after last death"), 1, 0)
        self.protector_clock = self._big_label("~00:10", 28)
        cadence_grid.addWidget(self.protector_clock, 1, 1)
        self.protector_button = self._large_button("Protector Died", "check-mark")
        self.protector_button.clicked.connect(self._mark_protector)
        cadence_grid.addWidget(self.protector_button, 1, 2)
        cadence_card.addLayout(cadence_grid)
        cadence_card.addWidget(
            self._muted(
                "These are predictive windows, not promises from the game. Other mechanics can delay Olms scheduling."
            )
        )
        top.addWidget(cadence_card, 2, 1)

        llothis_mechs = FoundryCard("Llothis Mechanics", "crossed-swords")
        llothis_mechs.addWidget(self._muted("Oppressive Bolts · 12+ sec · INTERRUPT"))
        llothis_mechs.addWidget(self._muted("Defiled Blast / cone · ~20–24 sec"))
        llothis_mechs.addWidget(self._muted("Teleport · ~25–35 sec"))
        top.addWidget(llothis_mechs, 3, 0)

        felms_mechs = FoundryCard("Felms Mechanics", "crossed-swords")
        felms_mechs.addWidget(self._muted("Teleport Strike / jump cycle · ~20 sec"))
        felms_mechs.addWidget(self._muted("Targets the furthest player; keep kite positioning deliberate."))
        top.addWidget(felms_mechs, 3, 1)

        notes = FoundryCard("Perfecta Notes", "feather").make_parchment()
        notes.addWidget(
            self._muted(
                "• Llothis first activation follows Olms' first jump.\n"
                "• Felms first activation follows Olms' second jump, around 75%.\n"
                "• Each mini gets a 3:00 active timer. Check health at 1:30 remaining; call execute at 0:30.\n"
                "• Deactivation starts a 1:00 respawn timer. At 0:15, prepare for the mini to return.\n"
                "• Perfecta target: 15:00 and no group deaths.\n"
                "• Use the manual buttons as the source of truth when the game delays or shifts an event."
            )
        )
        top.addWidget(notes, 4, 0, 1, 2)

        self.add_workspace_layout(top)

    def _mini_card(self, title: str, key: str) -> dict[str, object]:
        card = FoundryCard(title, "boss")
        state = QLabel("WAITING")
        state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        state.setStyleSheet("font-size: 21px; font-weight: 700;")
        card.addWidget(state)

        clock = self._big_label("--:--", 44)
        card.addWidget(clock)
        caption = self._muted("Waiting for first activation")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.addWidget(caption)

        progress = QProgressBar()
        progress.setRange(0, MINI_ENRAGE_SECONDS)
        progress.setValue(MINI_ENRAGE_SECONDS)
        progress.setTextVisible(False)
        card.addWidget(progress)

        milestones = self._muted("3:00 SPAWN        1:30 CHECK        0:30 EXECUTE        0:00 ENRAGE")
        milestones.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.addWidget(milestones)

        callout = QLabel("Waiting for first activation")
        callout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        callout.setWordWrap(True)
        callout.setStyleSheet("font-size: 18px; font-weight: 600;")
        card.addWidget(callout)

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
        card.addLayout(actions)

        return {
            "card": card,
            "state": state,
            "clock": clock,
            "caption": caption,
            "progress": progress,
            "callout": callout,
            "active": active,
            "inactive": inactive,
        }

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
        progress: QProgressBar = widgets["progress"]
        callout: QLabel = widgets["callout"]

        state_label.setText(mini.state.value.upper())
        callout.setText(mini.callout)

        if mini.state == MiniState.WAITING:
            clock.setText("--:--")
            caption.setText("Waiting for first activation")
            progress.setValue(MINI_ENRAGE_SECONDS)
            state_label.setStyleSheet("font-size: 21px; font-weight: 700;")
            return

        if mini.state == MiniState.INACTIVE:
            remaining = mini.respawn_remaining or 0.0
            clock.setText(format_clock(remaining))
            caption.setText(f"UNTIL RESPAWN ({format_clock(MINI_RESPAWN_SECONDS)})")
            progress.setValue(0)
            state_label.setStyleSheet("font-size: 21px; font-weight: 700; color: #C8A46A;")
            return

        remaining = mini.enrage_remaining or 0.0
        clock.setText(format_clock(remaining))
        caption.setText("TO ENRAGE (03:00)" if mini.state == MiniState.ACTIVE else "ENRAGED")
        progress.setValue(int(remaining))
        if mini.state == MiniState.ENRAGED:
            state_label.setStyleSheet("font-size: 21px; font-weight: 700; color: #D96A5B;")
        elif remaining <= 30:
            state_label.setStyleSheet("font-size: 21px; font-weight: 700; color: #E0A24C;")
        else:
            state_label.setStyleSheet("font-size: 21px; font-weight: 700; color: #76B68B;")

    def _refresh(self) -> None:
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
            f"Next jump: {next_jump}%" if next_jump is not None else "Execute · no further health jump"
        )
        self.kite_clock.setText(f"~{format_clock(self.model.kite_window_seconds)}")
        self.protector_clock.setText(f"~{format_clock(self.model.protector_window_seconds)}")

        failed = self.model.perfecta_status.startswith("FAILED")
        self.run_status.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #D96A5B;"
            if failed
            else "font-size: 22px; font-weight: 700; color: #76B6B0;"
        )

    def refresh_context(self) -> None:
        """Navigation hook kept for future encounter-driven timer profiles."""
        self._refresh()
