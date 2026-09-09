from __future__ import annotations

from PySide6.QtWidgets import QLabel

from services.rotation_support_cadence_progression_report_service import (
    RotationSupportCadenceProgressionReport,
)
from ui.components.foundry_card import FoundryCard


class RotationCadenceProgressionCard(FoundryCard):
    """Compact read-only explanation card for cadence optimization results."""

    def __init__(self, parent=None) -> None:
        super().__init__("Cadence Optimization", "compass", parent)
        self.set_watermark("compass", 0.035)
        self.setMaximumHeight(190)

        self.summary = QLabel("No cadence optimization has been applied yet.")
        self.summary.setWordWrap(True)
        self.addWidget(self.summary)

        self.detail = QLabel(
            "Accepted changes, winning rationale, stop reason, and unresolved mechanics will appear here."
        )
        self.detail.setWordWrap(True)
        self.detail.setProperty("muted", True)
        self.addWidget(self.detail)

    def clear_report(self) -> None:
        self.summary.setText("No cadence optimization has been applied yet.")
        self.detail.setText(
            "Accepted changes, winning rationale, stop reason, and unresolved mechanics will appear here."
        )

    def set_report(self, report: RotationSupportCadenceProgressionReport) -> None:
        accepted = int(report.advanced_steps)
        iterations = int(report.iterations)
        change_word = "change" if accepted == 1 else "changes"
        iteration_word = "iteration" if iterations == 1 else "iterations"
        self.summary.setText(
            f"{accepted} accepted {change_word} across {iterations} {iteration_word}. "
            f"{report.stop_summary}"
        )

        accepted_steps = tuple(
            step for step in report.steps if bool(getattr(step, "accepted", False))
        )
        latest = accepted_steps[-1] if accepted_steps else None
        parts: list[str] = []
        if latest is not None:
            if latest.promoted_rationale:
                parts.append(f"Latest accepted change: {latest.promoted_rationale}")
            if latest.promoted_reasons:
                parts.append("Why it won: " + "; ".join(latest.promoted_reasons))
        if report.unresolved:
            parts.append(f"Unresolved mechanics: {len(report.unresolved)} item(s).")
        elif not parts:
            parts.append("No accepted cadence change was needed.")

        self.detail.setText("  •  ".join(parts))


__all__ = ["RotationCadenceProgressionCard"]
