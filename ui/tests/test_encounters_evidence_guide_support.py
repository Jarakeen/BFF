from types import SimpleNamespace

from services.encounter_guide_evidence_projection_service import EncounterGuideTimelineRow
from ui.encounters_evidence_guide_support import _sync_event_lists, _timeline_rows


class _ListStub:
    def __init__(self, row: int = -1):
        self._row = row
        self.blocked = False

    def currentRow(self):
        return self._row

    def blockSignals(self, value):
        self.blocked = bool(value)

    def setCurrentRow(self, row):
        self._row = row


class _LabelStub:
    def __init__(self):
        self.text = ""

    def setText(self, value):
        self.text = value


def test_encounters_timeline_prefers_canonical_phases_over_reviewed_fallback():
    guide = SimpleNamespace(
        phases=(
            SimpleNamespace(
                threshold="65%",
                label="Canonical Phase",
                description="Persisted canonical phase row.",
            ),
        )
    )
    projection = SimpleNamespace(
        timeline=(EncounterGuideTimelineRow("P1", "Evidence Phase", "Reviewed fallback."),)
    )

    rows = _timeline_rows(None, guide, projection)

    assert rows == (("65%", "Canonical Phase", "Persisted canonical phase row."),)


def test_encounters_timeline_uses_reviewed_evidence_when_canonical_phases_are_missing():
    guide = SimpleNamespace(phases=())
    projection = SimpleNamespace(
        timeline=(
            EncounterGuideTimelineRow("P1", "Opening", "Reviewed opening phase."),
            EncounterGuideTimelineRow("50%", "Transition", "Reviewed threshold."),
        )
    )

    rows = _timeline_rows(None, guide, projection)

    assert rows == (
        ("P1", "Opening", "Reviewed opening phase."),
        ("50%", "Transition", "Reviewed threshold."),
    )


def test_encounters_timeline_lists_stay_synchronized_and_render_same_event():
    page = SimpleNamespace(
        encounter_phase_list=_ListStub(0),
        encounter_timeline_list=_ListStub(0),
        encounter_event_detail=_LabelStub(),
        _encounter_display_timeline=(
            ("P1", "Opening", "Opening details."),
            ("50%", "Transition", "Transition details."),
        ),
    )

    _sync_event_lists(page, 1, source="phase")

    assert page.encounter_timeline_list.currentRow() == 1
    assert "50% • Transition" in page.encounter_event_detail.text
    assert "Transition details." in page.encounter_event_detail.text
