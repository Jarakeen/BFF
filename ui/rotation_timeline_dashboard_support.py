from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from services.rotation_timeline_projection_service import RotationTimelineProjectionService
from ui.components.rotation_timeline_widget import RotationTimelineWidget


def install_rotation_timeline(page) -> None:
    """Add a visual Timeline/Details view without changing rotation authority."""
    if getattr(page, "_rotation_timeline_installed", False):
        return
    page._rotation_timeline_installed = True

    page.rotation_timeline_projection = RotationTimelineProjectionService()
    page.rotation_timeline_duration_evidence = None
    page.rotation_timeline_error = None
    page.rotation_timeline_widget = RotationTimelineWidget()

    controls = QWidget()
    controls_layout = QHBoxLayout(controls)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(6)

    page.rotation_timeline_view_button = QPushButton("Timeline")
    page.rotation_timeline_details_button = QPushButton("Details")
    page.rotation_timeline_view_button.setCheckable(True)
    page.rotation_timeline_details_button.setCheckable(True)
    page.rotation_timeline_view_button.setChecked(True)
    page.rotation_timeline_view_button.setProperty("primary", True)
    controls_layout.addWidget(page.rotation_timeline_view_button)
    controls_layout.addWidget(page.rotation_timeline_details_button)
    controls_layout.addStretch()

    body = page.timeline_table.parentWidget()
    body_layout = body.layout() if body is not None else None
    if body_layout is None:
        raise RuntimeError("rotation timeline table is not attached to a dashboard card body")

    body_layout.insertWidget(0, controls)
    body_layout.insertWidget(1, page.rotation_timeline_widget)
    page.timeline_table.setVisible(False)

    def show_timeline() -> None:
        page.rotation_timeline_view_button.setChecked(True)
        page.rotation_timeline_details_button.setChecked(False)
        page.rotation_timeline_widget.setVisible(True)
        page.timeline_table.setVisible(False)

    def show_details() -> None:
        page.rotation_timeline_view_button.setChecked(False)
        page.rotation_timeline_details_button.setChecked(True)
        page.rotation_timeline_widget.setVisible(False)
        page.timeline_table.setVisible(True)

    page.rotation_timeline_view_button.clicked.connect(show_timeline)
    page.rotation_timeline_details_button.clicked.connect(show_details)

    def refresh_visual_timeline() -> bool:
        """Refresh optional visual evidence without becoming rotation authority.

        The RotationPlan/details path must remain usable even if a visual-only
        projection or rendering dependency fails.  A timeline failure is retained
        as explicit UI evidence instead of being allowed to abort Generate Rotation.
        """
        plan = getattr(page, "rotation_plan", None)
        if plan is None:
            page.rotation_timeline_error = None
            page.rotation_timeline_widget.clear_projection()
            return True
        try:
            projection = page.rotation_timeline_projection.project(
                plan,
                duration_evidence=page.rotation_timeline_duration_evidence,
            )
            page.rotation_timeline_widget.set_projection(projection)
        except Exception as exc:  # visual-only boundary; never invalidate the plan
            page.rotation_timeline_error = str(exc) or exc.__class__.__name__
            page.rotation_timeline_widget.clear_projection()
            return False
        page.rotation_timeline_error = None
        return True

    page.refresh_visual_rotation_timeline = refresh_visual_timeline

    original_set_plan = page.set_rotation_plan

    def set_plan_with_timeline(plan) -> None:
        page.rotation_timeline_duration_evidence = None
        original_set_plan(plan)
        refresh_visual_timeline()

    page.set_rotation_plan = set_plan_with_timeline

    original_clear_plan = page.clear_rotation_plan

    def clear_plan_with_timeline(*, refresh: bool = True) -> None:
        page.rotation_timeline_duration_evidence = None
        original_clear_plan(refresh=refresh)
        refresh_visual_timeline()

    page.clear_rotation_plan = clear_plan_with_timeline

    original_set_duration_evidence = page.duration_evidence_card.set_evidence

    def set_duration_evidence_with_timeline(evidence) -> None:
        original_set_duration_evidence(evidence)
        page.rotation_timeline_duration_evidence = evidence
        refresh_visual_timeline()

    page.duration_evidence_card.set_evidence = set_duration_evidence_with_timeline

    original_clear_duration_evidence = page.duration_evidence_card.clear_evidence

    def clear_duration_evidence_with_timeline() -> None:
        original_clear_duration_evidence()
        page.rotation_timeline_duration_evidence = None
        refresh_visual_timeline()

    page.duration_evidence_card.clear_evidence = clear_duration_evidence_with_timeline

    refresh_visual_timeline()


__all__ = ["install_rotation_timeline"]
