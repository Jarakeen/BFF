import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QComboBox, QTableWidget, QVBoxLayout, QWidget

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_timeline_projection_service import RotationTimelineAction
from ui.components.rotation_timeline_widget import _RotationTimelineCanvas
from ui.rotation_duration_evidence_support import (
    RotationDurationEvidence,
    RotationDurationEvidenceRow,
)
from ui import rotation_timeline_dashboard_support as timeline_support_module
from ui.rotation_timeline_dashboard_support import (
    RotationTimelineIconResolver,
    install_rotation_timeline,
)


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
        self.rotation_type_combo = QComboBox()
        self.rotation_type_combo.addItems(["Static", "Semi-static", "Dynamic"])
        self.rotation_type_combo.setCurrentText("Semi-static")

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


def test_unimplemented_rotation_modes_remain_visible_but_disabled():
    page = _FakePage()
    install_rotation_timeline(page)

    assert [page.rotation_type_combo.itemText(i) for i in range(page.rotation_type_combo.count())] == [
        "Static",
        "Semi-static",
        "Dynamic",
    ]
    model = page.rotation_type_combo.model()
    assert not model.item(0).isEnabled()
    assert model.item(1).isEnabled()
    assert not model.item(2).isEnabled()
    assert page.rotation_type_combo.currentText() == "Semi-static"


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


def test_visual_timeline_failure_does_not_abort_authoritative_plan(monkeypatch):
    page = _FakePage()
    install_rotation_timeline(page)

    def explode(*args, **kwargs):
        raise RuntimeError("icon lookup exploded")

    monkeypatch.setattr(page.rotation_timeline_projection, "project", explode)

    plan = _plan()
    page.set_rotation_plan(plan)

    assert page.rotation_plan is plan
    assert page.rotation_timeline_widget.canvas._projection is None
    assert page.rotation_timeline_error == "icon lookup exploded"
    assert page.refresh_visual_rotation_timeline() is False


def test_timeline_icon_resolver_accepts_canonical_skill_identity(monkeypatch, tmp_path):
    icon_root = tmp_path / "assets" / "AbilityIcons" / "icons" / "128"
    icon_root.mkdir(parents=True)
    icon_path = icon_root / "ability_restorationstaff_001.png"
    pixmap = QPixmap(8, 8)
    assert pixmap.save(str(icon_path))

    def fake_resource_path(*parts):
        return tmp_path.joinpath(*parts)

    monkeypatch.setattr(timeline_support_module, "get_resource_path", fake_resource_path)
    monkeypatch.setattr(
        timeline_support_module,
        "load_skill_choices",
        lambda: [
            {
                "name": "Combat Prayer",
                "index_name": "combat_prayer",
                "texture": "/esoui/art/icons/ability_restorationstaff_001.dds",
            }
        ],
    )

    resolver = RotationTimelineIconResolver()
    resolved = resolver.resolve("combat_prayer", "combat_prayer")
    assert resolved == str(icon_path)

    action = RotationTimelineAction(
        time_seconds=0.0,
        sequence=0,
        name="combat_prayer",
        kind="skill",
        bar="front",
        icon_key="combat_prayer",
        icon_path=resolved,
    )
    rendered = _RotationTimelineCanvas._icon_pixmap(action)
    assert rendered is not None
    assert not rendered.isNull()

    first_candidate = _RotationTimelineCanvas._candidate_icon_paths(action)[0]
    assert first_candidate.name == "combat_prayer.png"
