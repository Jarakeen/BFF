from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QWidget

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_timeline_projection_service import RotationTimelineProjection
from ui import rotation_pdf_export_support as export_support_module
from ui.rotation_pdf_export_support import install_rotation_pdf_export


_APP = QApplication.instance() or QApplication([])


class _Status:
    def __init__(self) -> None:
        self.successes: list[str] = []
        self.warnings: list[str] = []

    def success(self, message: str) -> None:
        self.successes.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class _Exporter:
    def __init__(self) -> None:
        self.calls = []

    def export(self, **kwargs):
        self.calls.append(kwargs)
        return Path(kwargs["path"])


class _Page:
    def __init__(self, projection: RotationTimelineProjection) -> None:
        self.rotation_plan = None
        self.rotation_timeline_error = None
        self.rotation_timeline_widget = SimpleNamespace(
            canvas=SimpleNamespace(_projection=projection)
        )
        controls = QWidget()
        controls.setLayout(QHBoxLayout())
        self.rotation_timeline_view_button = QPushButton("Timeline", controls)
        self.rotation_timeline_details_button = QPushButton("Details", controls)
        controls.layout().addWidget(self.rotation_timeline_view_button)
        controls.layout().addWidget(self.rotation_timeline_details_button)
        controls.layout().addStretch()
        self._controls = controls

        self.resource_summary = QLabel("Magicka sustain: SUSTAINS")
        self.resource_detail = QLabel("Minimum: 12000")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlainText("Keep support buffs stable.")
        self.status = _Status()
        self.build = SimpleNamespace(Role="Healer", EsoClass="Warden", Race="Breton")

    def _selected_build(self):
        return self.build

    def rotation_settings(self):
        return {
            "rotation_type": "Semi-static",
            "target_type": "Single Target",
        }

    def set_rotation_plan(self, plan) -> None:
        self.rotation_plan = plan

    def clear_rotation_plan(self, *, refresh: bool = True) -> None:
        self.rotation_plan = None


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
        ),
    )


def _projection() -> RotationTimelineProjection:
    return RotationTimelineProjection(
        duration_seconds=60.0,
        actions=(),
        lanes=(),
        unresolved=(),
    )


def test_export_button_tracks_plan_state_and_uses_exact_materialized_projection(monkeypatch, tmp_path) -> None:
    projection = _projection()
    page = _Page(projection)
    exporter = _Exporter()
    output = tmp_path / "Magrat_DF_Healer_rotation.pdf"

    monkeypatch.setattr(
        export_support_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(output), "PDF Files (*.pdf)"),
    )

    install_rotation_pdf_export(page, exporter=exporter)

    assert page.export_rotation_pdf_button.isEnabled() is False
    assert page._controls.layout().indexOf(page.export_rotation_pdf_button) == 2

    plan = _plan()
    page.set_rotation_plan(plan)
    assert page.export_rotation_pdf_button.isEnabled() is True

    page.export_current_rotation_pdf()

    assert len(exporter.calls) == 1
    call = exporter.calls[0]
    assert call["plan"] is plan
    assert call["projection"] is projection
    assert call["path"] == output
    assert call["include_details"] is True
    assert call["context"].role == "Healer"
    assert call["context"].eso_class == "Warden"
    assert call["context"].race == "Breton"
    assert call["context"].rotation_mode == "Semi-static"
    assert call["context"].target_type == "Single Target"
    assert call["context"].sustain_summary == "Magicka sustain: SUSTAINS"
    assert call["context"].notes == "Keep support buffs stable."
    assert page.status.warnings == []
    assert len(page.status.successes) == 1

    page.clear_rotation_plan(refresh=False)
    assert page.export_rotation_pdf_button.isEnabled() is False
