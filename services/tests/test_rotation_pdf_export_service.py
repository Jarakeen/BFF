from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_pdf_export_service import (
    RotationPdfExportContext,
    RotationPdfExportService,
)
from services.rotation_timeline_projection_service import (
    RotationTimelineAction,
    RotationTimelineLane,
    RotationTimelineProjection,
    RotationTimelineSegment,
)


def _plan(duration: float = 60.0) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=duration,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(1.0, 1, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(15.0, 2, RotationActionKind.SKILL, "Budding Seeds", "front"),
            RotationAction(31.0, 3, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(32.0, 4, RotationActionKind.SKILL, "Winter's Revenge", "back"),
        ),
        assumptions=("sample assumption",),
        unresolved=("sample unresolved",),
    )


def _projection(duration: float = 60.0) -> RotationTimelineProjection:
    return RotationTimelineProjection(
        duration_seconds=duration,
        actions=(
            RotationTimelineAction(
                time_seconds=0.0,
                sequence=0,
                name="Combat Prayer",
                kind="skill",
                bar="front",
                icon_key="combat_prayer",
                icon_path=None,
            ),
            RotationTimelineAction(
                time_seconds=15.0,
                sequence=2,
                name="Budding Seeds",
                kind="skill",
                bar="front",
                icon_key="budding_seeds",
                icon_path=None,
            ),
            RotationTimelineAction(
                time_seconds=32.0,
                sequence=4,
                name="Winter's Revenge",
                kind="skill",
                bar="back",
                icon_key="winter_s_revenge",
                icon_path=None,
            ),
        ),
        lanes=(
            RotationTimelineLane(
                lane_key="combat_prayer:front",
                label="Combat Prayer",
                bar="front",
                duration_seconds=10.0,
                segments=(
                    RotationTimelineSegment(0.0, 10.0),
                    RotationTimelineSegment(28.0, 38.0),
                ),
            ),
        ),
        unresolved=("sample unresolved",),
    )


def test_mobile_timeline_windows_split_long_rotation_into_readable_sections() -> None:
    assert RotationPdfExportService.timeline_windows(60.0) == (
        (0.0, 30.0),
        (30.0, 60.0),
    )
    assert RotationPdfExportService.timeline_windows(75.0) == (
        (0.0, 30.0),
        (30.0, 60.0),
        (60.0, 75.0),
    )


def test_export_writes_pdf_from_materialized_plan_and_projection(tmp_path) -> None:
    output = tmp_path / "magrat_rotation.pdf"

    result = RotationPdfExportService().export(
        plan=_plan(),
        projection=_projection(),
        path=output,
        context=RotationPdfExportContext(
            role="Healer",
            eso_class="Warden",
            race="Breton",
            rotation_mode="Semi-static",
            target_type="Single Target",
            sustain_summary="Magicka sustain: SUSTAINS",
            sustain_detail="Minimum: 12000",
            notes="Keep support buffs stable through mechanic windows.",
        ),
        include_details=True,
    )

    assert result == output
    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF")
    assert output.stat().st_size > 1500


def test_export_refuses_mismatched_plan_and_projection_horizons(tmp_path) -> None:
    try:
        RotationPdfExportService().export(
            plan=_plan(60.0),
            projection=_projection(30.0),
            path=tmp_path / "mismatch.pdf",
        )
    except ValueError as exc:
        assert "durations to match" in str(exc)
    else:
        raise AssertionError("mismatched rotation plan/projection durations must be rejected")
