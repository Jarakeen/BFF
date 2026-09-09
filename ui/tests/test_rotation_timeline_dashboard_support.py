import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidget, QVBoxLayout, QWidget

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from ui.rotation_duration_evidence_support import (
    RotationDurationEvidence,
    RotationDurationEvidenceRow,
)
from ui.rotation_timeline_dashboard_support import install_rotation_timeline


_APP = QApplication.instance() or QApplication([])


class _DurationEvidenceCard:
    def __init__(self) -> None:
        self.evidence = None

    def set_evidence(self, evidence) -> None:
        self.evidence = evidence

    def clear_evidence(self) -> None:
        self.evidence = None


class _FakePage:
    def __init__(self) -> None:
        self.rotation_plan = None
        self.timeline_body = QWidget()
        self.timeline_body.setLayout(QVBoxLayout())
        self.timeline_table = QTableWidget()
        self.timeline_body.layout().addWidget(self.timeline_table)
        self.duration_evidence_card = _DurationEvidenceCard()

    def set_rotation_plan(self, plan) -> None:
        self.rotation_plan = plan

    def clear_rotation_plan(self, *, refresh: bool = True) -> None:
        self.rotation_plan = None


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(8.0, 1, RotationActionKind.SKILL, "Combat Prayer", "front"),
        ),
    )


def _duration_evidence() -> RotationDurationEvidence:
    return RotationDurationEvidence(
        rows=(
            RotationDurationEvidenceRow(
                ability="Combat Prayer",
                bar="Front",
                duration_seconds=10.0,
                casts=2,
                uptime_percent=90.0,
                gap_seconds=2.0,
                premature_seconds=2.0,
            ),
        ),
        summary="resolved",
        detail="resolved duration",
        unresolved=(),
    )


def test_install_defaults_to_visual_timeline_and_preserves_details_toggle():
    page = _FakePage()
    install_rotation_timeline(page)

    assert page.rotation_timeline_widget.isVisible() is False or page.rotation_timeline_widget.isHidden() is False
    assert page.timeline_table.isHidden()
    assert page.rotation_timeline_view_button.isChecked()
    assert not page.rotation_timeline_details_button.isChecked()

    page.rotation_timeline_details_button.click()
    assert page.rotation_timeline_widget.isHidden()
    assert not page.timeline_table.isHidden()

    page.rotation_timeline_view_button.click()
    assert not page.rotation_timeline_widget.isHidden()
    assert page.timeline_table.isHidden()


def test_plan_and_duration_wrappers_refresh_one_shared_visual_projection():
    page = _FakePage()
    install_rotation_timeline(page)

    page.set_rotation_plan(_plan())
    initial = page.rotation_timeline_widget.canvas._projection
    assert initial is not None
    assert len(initial.actions) == 2
    assert initial.lanes == ()

    page.duration_evidence_card.set_evidence(_duration_evidence())
    projected = page.rotation_timeline_widget.canvas._projection
    assert projected is not None
    assert len(projected.lanes) == 1
    assert projected.lanes[0].segments[0].start_seconds == 0.0
    assert projected.lanes[0].segments[0].end_seconds == 18.0

    page.clear_rotation_plan(refresh=False)
    assert page.rotation_timeline_widget.canvas._projection is None
