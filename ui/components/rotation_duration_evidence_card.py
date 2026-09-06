from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)

from ui.components.foundry_card import FoundryCard
from ui.rotation_duration_evidence_support import RotationDurationEvidence


class RotationDurationEvidenceCard(FoundryCard):
    """Read-only Duration / Uptime evidence for one generated rotation.

    The card formats evidence supplied by ``RotationDurationEvidenceSupport``.
    It does not resolve durations, analyze recasts, or mutate a rotation plan.
    """

    def __init__(self, parent=None):
        super().__init__("Duration / Uptime", "◷", parent)
        self.set_watermark("compass", 0.035)

        self.summary_label = QLabel("No duration evidence generated yet.")
        self.summary_label.setWordWrap(True)
        self.addWidget(self.summary_label)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Bar",
                "Ability",
                "Duration",
                "Casts",
                "Uptime",
                "Gap",
                "Early",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(170)
        self.addWidget(self.table)

        self.detail_label = QLabel(
            "Canonical positive skill durations will populate recast evidence here."
        )
        self.detail_label.setWordWrap(True)
        self.detail_label.setProperty("muted", True)
        self.addWidget(self.detail_label)

    def set_evidence(self, evidence: RotationDurationEvidence) -> None:
        self.summary_label.setText(evidence.summary)
        self.detail_label.setText(evidence.detail)
        self.table.setRowCount(0)

        for item in evidence.rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (
                item.bar,
                item.ability,
                f"{item.duration_seconds:g}s",
                str(item.casts),
                f"{item.uptime_percent:.1f}%",
                f"{item.gap_seconds:.1f}s",
                f"{item.premature_seconds:.1f}s",
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def clear_evidence(self) -> None:
        self.table.setRowCount(0)
        self.summary_label.setText("No duration evidence generated yet.")
        self.detail_label.setText(
            "Canonical positive skill durations will populate recast evidence here."
        )
