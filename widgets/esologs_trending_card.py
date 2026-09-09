from __future__ import annotations

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
from services.esologs_trending_service import EsoLogsTrendingReport, RoleTrendingSummary
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
    """Role-aware popularity snapshot across top individual ESO Logs players."""

    def __init__(self, service_factory, parent=None):
        super().__init__(title="ESO Logs Trending", icon="achievement", parent=parent)
        self._service_factory = service_factory
        self._trials: list[dict] = []
        self._sections: dict[str, dict[str, QLabel]] = {}
        self._build_ui()
        self._connect_signals()
        self.load_trials()

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
            "individual players per role and shows the gear most commonly observed "
            "among those DDs, healers, and tanks."
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
            gear_label.setTextInteractionFlags(gear_label.textInteractionFlags())
            layout.addWidget(gear_label)

            class_heading = QLabel("Top Classes")
            class_heading.setFont(Fonts.label())
            layout.addWidget(class_heading)

            class_label = QLabel("No data loaded.")
            class_label.setWordWrap(True)
            layout.addWidget(class_label)

            loadout_heading = QLabel("Top Player Loadouts")
            loadout_heading.setFont(Fonts.label())
            layout.addWidget(loadout_heading)

            loadout_label = QLabel("No data loaded.")
            loadout_label.setWordWrap(True)
            loadout_label.setTextInteractionFlags(loadout_label.textInteractionFlags())
            layout.addWidget(loadout_label)
            layout.addStretch()

            section.addWidget(content)
            board_layout.addWidget(section, 1)

            self._sections[role_key] = {
                "count": count_label,
                "gear": gear_label,
                "classes": class_label,
                "loadouts": loadout_label,
            }

        scroll.setWidget(board)
        root_layout.addWidget(scroll, 1)

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
            "Popularity is descriptive ESO Logs evidence, not canonical best-in-slot."
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
                "\n".join(
                    f"{index}. {row.name} — {row.count}/{row.player_count} ({row.percent:.0f}%)"
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

        examples: list[str] = []
        for player in summary.sample_players:
            class_name = player.ClassName or "Unknown class"
            gear = " · ".join(player.GearSets) if player.GearSets else "No sets exposed"
            examples.append(f"{player.Name} — {class_name}\n  {gear}")
        refs["loadouts"].setText(
            "\n\n".join(examples) if examples else "No ranked player loadouts available."
        )


__all__ = ["EsoLogsTrendingCard"]
