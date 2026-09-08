from __future__ import annotations

"""Replace the placeholder overview practice list with pinned Performance Focus goals."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from engine.config import get_data_dir
from services.performance_focus_service import PerformanceFocusStore
from ui.components.foundry_card import FoundryCard

_INSTALLED = False


def _focus_store() -> PerformanceFocusStore:
    return PerformanceFocusStore(get_data_dir() / "performance_focus.json")


def _goal_widget(goal) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 1, 0, 1)
    layout.setSpacing(2)

    header = QHBoxLayout()
    name = QLabel(goal.Name)
    name.setProperty("overviewGoalName", True)
    header.addWidget(name, 1)

    if goal.CurrentPercent is None:
        value = QLabel(f"target {goal.TargetPercent:.0f}%")
    else:
        value = QLabel(f"{goal.CurrentPercent:.1f}% → {goal.TargetPercent:.0f}%")
    value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    header.addWidget(value)
    layout.addLayout(header)

    if goal.CurrentPercent is not None:
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(max(0, min(100, int(round(goal.CurrentPercent)))))
        bar.setTextVisible(False)
        bar.setFixedHeight(7)
        layout.addWidget(bar)

    detail_bits = []
    if goal.EvidenceNote:
        detail_bits.append(goal.EvidenceNote)
    if goal.FightName:
        detail_bits.append(f"from {goal.FightName}")
    detail = QLabel(" • ".join(detail_bits) or goal.Source)
    detail.setWordWrap(True)
    detail.setProperty("muted", True)
    layout.addWidget(detail)
    return box


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.operations_console import OperationsConsole

    def performance_focus_card(self, build) -> FoundryCard:
        del build
        goals = _focus_store().load()
        card = FoundryCard("Next Raid Focus")

        if not goals:
            empty = QLabel(
                "No focus goals pinned yet. Review a run in Capabilities → Performance Dashboard, then pin the uptimes that are actually your responsibility."
            )
            empty.setWordWrap(True)
            card.addWidget(empty)
            card.addStretch(1)
            card.addWidget(self._compact_button("Open Performance Focus"))
            return card

        for goal in goals[:4]:
            card.addWidget(_goal_widget(goal))

        if len(goals) > 4:
            extra = QLabel(f"… and {len(goals) - 4} more pinned goal(s)")
            extra.setProperty("muted", True)
            card.addWidget(extra)

        card.addStretch(1)
        card.addWidget(self._compact_button("Open Performance Focus"))
        return card

    OperationsConsole._skills_to_work_on_card = performance_focus_card
    _INSTALLED = True
