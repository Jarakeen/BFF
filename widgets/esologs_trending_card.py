from __future__ import annotations

from html import escape
from urllib.parse import quote, unquote

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from services.esologs_client import EsoLogsApiError
from services.esologs_trending_service import (
    EsoLogsTrendingReport,
    RoleTrendingSummary,
    TrendMovementItem,
)
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_status_badge import FoundryStatusBadge
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts

_ROLE_SECTIONS = (
    ("dps", "DD"),
    ("healer", "Healer"),
    ("tank", "Tank"),
)
_TOP_GEAR_ROWS = 10
_TOP_CLASS_ROWS = 5


class EsoLogsTrendingCard(FoundryCard):
    """Role-aware popularity and momentum snapshot for top ESO Logs players."""

    setRequested = Signal(str)

    def __init__(self, service_factory, parent=None):
        super().__init__(title="ESO Logs Trending", icon="achievement", parent=parent)
        self._service_factory = service_factory
        self._trials: list[dict] = []
        self._sections: dict[str, dict[str, QLabel]] = {}
        self._build_ui()
        self._connect_signals()
        self.load_trials()

    def _emit_set_link(self, href: str) -> None:
        if not href.startswith("set:"):
            return
        set_name = unquote(href[4:])
        self.setRequested.emit(set_name)

        # MainWindow already owns the canonical Gear Lookup page. Route there
        # directly when hosted in the real app; keep the signal above for tests or
        # alternate hosts. This avoids introducing a second gear-detail surface.
        window = self.window()
        pages = getattr(window, "pages", {})
        gear_page = pages.get("gear_lookup") if isinstance(pages, dict) else None
        show_page = getattr(window, "show_page", None)
        if gear_page is None or not callable(show_page):
            return

        # Clear Gear Lookup facets so an exact-name navigation cannot be hidden by
        # whatever filters the user happened to leave selected last time.
        for combo_name in ("weight", "bonus", "acquisition_type"):
            combo = getattr(gear_page, combo_name, None)
            if combo is not None and hasattr(combo, "setCurrentIndex"):
                combo.setCurrentIndex(0)

        search = getattr(gear_page, "search", None)
        results = getattr(gear_page, "results", None)
        if search is not None:
            search.setText(set_name)
        if results is not None:
            for index in range(results.count()):
                item = results.item(index)
                if item is not None and item.text().strip().casefold() == set_name.casefold():
                    results.setCurrentItem(item)
                    break

        show_page("gear_lookup")

    @staticmethod
    def _set_link(name: str) -> str:
        return f'<a href="set:{quote(name, safe="")}">{escape(name)}</a>'

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(10)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)

        self.trial_combo = QComboBox()
        self.trial_combo.setPlaceholderText("Choose a trial...")
        self.encounter_combo = QComboBox()
        self.encounter_combo.setPlaceholderText("Choose a boss...")
        self.encounter_combo.setEnabled(False)

        self.fetch_button = FoundryButton(
            "Analyze Top Players",
            role=ButtonRole.PRIMARY,
            compact=True,
        )
        self.fetch_button.setEnabled(False)

        self.reload_button = FoundryButton(
            "Reload",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        picker_row.addWidget(self.trial_combo, 1)
        picker_row.addWidget(self.encounter_combo, 1)
        picker_row.addWidget(self.fetch_button)
        picker_row.addWidget(self.reload_button)
        root_layout.addLayout(picker_row)

        self.summary = QLabel(
            "Choose a trial and boss. This view inspects up to five top-ranked "
            "individual players per role, then compares the current set usage with "
            "your previous saved snapshot for that same boss."
        )
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        root_layout.addWidget(self.summary)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        board = QWidget()
        board_layout = QHBoxLayout(board)
        board_layout.setContentsMargins(0, 0, 0, 0)
        board_layout.setSpacing(10)

        for role_key, role_label in _ROLE_SECTIONS:
            section = FoundryCard(title=f"{role_label} Trends")
            section.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )

            content = QWidget()
            layout = QVBoxLayout(content)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)

            header = QHBoxLayout()
            badge = FoundryStatusBadge(role_label, scale="role", key=role_key)
            count_label = QLabel("0 ranked players")
            count_label.setFont(Fonts.small())
            count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
            header.addWidget(badge)
            header.addWidget(count_label)
            header.addStretch()
            layout.addLayout(header)

            gear_heading = QLabel("Top Gear Sets")
            gear_heading.setFont(Fonts.label())
            layout.addWidget(gear_heading)

            gear_label = QLabel("No data loaded.")
            gear_label.setWordWrap(True)
            gear_label.setOpenExternalLinks(False)
            gear_label.linkActivated.connect(self._emit_set_link)
            layout.addWidget(gear_label)

            class_heading = QLabel("Top Classes")
            class_heading.setFont(Fonts.label())
            layout.addWidget(class_heading)

            class_label = QLabel("No data loaded.")
            class_label.setWordWrap(True)
            layout.addWidget(class_label)

            movement_labels: dict[str, QLabel] = {}
            for key, heading in (
                ("making_waves", "Making Waves"),
                ("cooling_off", "Cooling Off"),
                ("new_arrivals", "New Arrival"),
                ("breakouts", "Breakout"),
            ):
                heading_label = QLabel(heading)
                heading_label.setFont(Fonts.label())
                layout.addWidget(heading_label)

                value_label = QLabel("Needs another snapshot.")
                value_label.setWordWrap(True)
                value_label.setOpenExternalLinks(False)
                value_label.linkActivated.connect(self._emit_set_link)
                layout.addWidget(value_label)
                movement_labels[key] = value_label

            layout.addStretch()
            section.addWidget(content)
            board_layout.addWidget(section, 1)

            self._sections[role_key] = {
                "count": count_label,
                "gear": gear_label,
                "classes": class_label,
                **movement_labels,
            }

        scroll.setWidget(board)
        root_layout.addWidget(scroll, 1)

        fun_note = QLabel(
            "*Just for fun: movement signals compare your saved ESO Logs snapshots. "
            "They describe what ranked players are wearing, not what the game declares best-in-slot."
        )
        fun_note.setWordWrap(True)
        fun_note.setFont(Fonts.small())
        fun_note.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        root_layout.addWidget(fun_note)

        self.status = FoundryStatusBar()
        self.status.message.setWordWrap(True)
        root_layout.addWidget(self.status)

        self.addWidget(root)

    def _connect_signals(self) -> None:
        self.trial_combo.currentIndexChanged.connect(self._on_trial_changed)
        self.encounter_combo.currentIndexChanged.connect(self._on_encounter_changed)
        self.fetch_button.clicked.connect(self.fetch_trending)
        self.reload_button.clicked.connect(self.load_trials)

    def load_trials(self) -> None:
        self.status.info("Loading trial list from ESO Logs...")
        try:
            self._trials = self._service_factory().list_trials()
        except EsoLogsApiError as exc:
            self.status.error(str(exc))
            return
        except Exception as exc:
            self.status.error(f"Failed to load trials: {exc}")
            return

        self.trial_combo.blockSignals(True)
        self.trial_combo.clear()
        for trial in self._trials:
            self.trial_combo.addItem(trial["name"], trial)
        self.trial_combo.setCurrentIndex(-1)
        self.trial_combo.blockSignals(False)

        self.encounter_combo.blockSignals(True)
        self.encounter_combo.clear()
        self.encounter_combo.setEnabled(False)
        self.encounter_combo.blockSignals(False)
        self.fetch_button.setEnabled(False)

        if self._trials:
            self.status.info(f"{len(self._trials)} ranked trial zone(s) loaded.")
        else:
            self.status.warning("ESO Logs returned no ranked trial zones.")

    def _on_trial_changed(self, index: int) -> None:
        self.encounter_combo.blockSignals(True)
        self.encounter_combo.clear()
        self.fetch_button.setEnabled(False)

        if index < 0:
            self.encounter_combo.setEnabled(False)
            self.encounter_combo.blockSignals(False)
            return

        trial = self.trial_combo.itemData(index) or {}
        for encounter in trial.get("encounters", []):
            self.encounter_combo.addItem(encounter["name"], encounter)
        self.encounter_combo.setCurrentIndex(-1)
        self.encounter_combo.setEnabled(True)
        self.encounter_combo.blockSignals(False)

    def _on_encounter_changed(self, index: int) -> None:
        self.fetch_button.setEnabled(index >= 0)

    def fetch_trending(self) -> None:
        trial_index = self.trial_combo.currentIndex()
        encounter_index = self.encounter_combo.currentIndex()
        if trial_index < 0 or encounter_index < 0:
            self.status.warning("Choose a trial and boss first.")
            return

        trial = self.trial_combo.itemData(trial_index) or {}
        encounter = self.encounter_combo.itemData(encounter_index) or {}
        self.status.info(
            f"Loading top-ranked {encounter.get('name', 'encounter')} players..."
        )
        self.fetch_button.setEnabled(False)

        try:
            report = self._service_factory().analyze_encounter(
                zone_id=int(trial["id"]),
                zone_name=str(trial["name"]),
                encounter_id=int(encounter["id"]),
                encounter_name=str(encounter["name"]),
                player_limit=5,
            )
        except EsoLogsApiError as exc:
            self.status.error(str(exc))
            return
        except Exception as exc:
            self.status.error(f"Trending analysis failed: {exc}")
            return
        finally:
            self.fetch_button.setEnabled(True)

        self._render_report(report)
        skipped = (
            f"; {report.ranked_players_skipped} skipped"
            if report.ranked_players_skipped
            else ""
        )
        self.status.success(
            f"Analyzed {report.ranked_players_analyzed} top-ranked player(s){skipped}."
        )

    def _render_report(self, report: EsoLogsTrendingReport) -> None:
        self.summary.setText(
            f"{report.trial_name} · {report.encounter_name} · "
            f"{report.ranked_players_analyzed} top-ranked player observations. "
            "Popularity and movement are descriptive ESO Logs evidence, not canonical best-in-slot."
        )
        for role_key, _ in _ROLE_SECTIONS:
            self._render_role(report.role_summaries[role_key])

    def _render_role(self, summary: RoleTrendingSummary) -> None:
        refs = self._sections[summary.role]
        refs["count"].setText(
            f"{summary.player_count} ranked player"
            f"{'s' if summary.player_count != 1 else ''}"
        )

        if summary.gear_sets:
            refs["gear"].setText(
                "<br>".join(
                    f"{index}. {self._set_link(row.name)} — "
                    f"{row.count}/{row.player_count} ({row.percent:.0f}%)"
                    for index, row in enumerate(
                        summary.gear_sets[:_TOP_GEAR_ROWS], start=1
                    )
                )
            )
        else:
            refs["gear"].setText("No gear-set names were exposed for this role.")

        if summary.classes:
            refs["classes"].setText(
                "\n".join(
                    f"{index}. {row.name} — {row.count}/{row.player_count} ({row.percent:.0f}%)"
                    for index, row in enumerate(
                        summary.classes[:_TOP_CLASS_ROWS], start=1
                    )
                )
            )
        else:
            refs["classes"].setText("No class data was exposed for this role.")

        if not summary.has_history:
            for key in ("making_waves", "cooling_off", "new_arrivals", "breakouts"):
                refs[key].setText("Needs another snapshot.")
            return

        refs["making_waves"].setText(
            self._movement_html(summary.making_waves)
            if summary.making_waves
            else "No sets rising quickly outside the top 10."
        )
        refs["cooling_off"].setText(
            self._movement_html(summary.cooling_off)
            if summary.cooling_off
            else "No meaningful declines detected."
        )
        refs["new_arrivals"].setText(
            self._movement_html(summary.new_arrivals)
            if summary.new_arrivals
            else "No new sets appeared in this snapshot."
        )
        refs["breakouts"].setText(
            self._movement_html(summary.breakouts)
            if summary.breakouts
            else "No sets broke into the top 10."
        )

    def _movement_html(self, rows: tuple[TrendMovementItem, ...]) -> str:
        lines = []
        for row in rows:
            sign = "+" if row.delta_points > 0 else ""
            rank = f" • #{row.current_rank}" if row.current_rank is not None else ""
            lines.append(
                f"{self._set_link(row.name)} — {row.current_percent:.0f}% "
                f"({sign}{row.delta_points:.0f} pts){rank}"
            )
        return "<br>".join(lines)


__all__ = ["EsoLogsTrendingCard"]
