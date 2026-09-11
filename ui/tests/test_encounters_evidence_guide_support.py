from pathlib import Path
from types import SimpleNamespace

from services.encounter_boss_guide import EncounterBossGuideNotFound
from services.encounter_guide_evidence_projection_service import EncounterGuideTimelineRow
from ui.encounters_evidence_guide_support import (
    _display_guide,
    _reviewed_boss_rows,
    _sync_event_lists,
    _timeline_rows,
)


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


class _GuideStub:
    def __init__(self, data_root: Path):
        self.database = data_root / "eso.db"

    def get(self, encounter_id: str):
        if encounter_id == "lylanar_turlassil":
            raise EncounterBossGuideNotFound(encounter_id)
        if encounter_id == "lylanar":
            return SimpleNamespace(
                phases=(
                    SimpleNamespace(
                        threshold="65%",
                        label="Lylanar transition",
                        description="Reviewed member phase.",
                    ),
                )
            )
        if encounter_id == "turlassil":
            return SimpleNamespace(phases=())
        raise EncounterBossGuideNotFound(encounter_id)


def _repo_data_root() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


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


def test_reviewed_dreadsail_selector_groups_twins_and_excludes_raw_members():
    page = SimpleNamespace(guide_service=SimpleNamespace(database=_repo_data_root() / "eso.db"))

    rows = _reviewed_boss_rows(page, "Dreadsail Reef")
    ids = [row.encounter_id for row in rows]

    assert ids == ["lylanar_turlassil", "reef_guardian", "tideborn_taleria"]
    assert "lylanar" not in ids
    assert "turlassil" not in ids
    assert rows[0].name == "Lylanar and Turlassil"


def test_grouped_encounter_can_collect_canonical_member_phases_without_fake_db_row():
    data_root = _repo_data_root()
    page = SimpleNamespace(guide_service=_GuideStub(data_root))

    guide = _display_guide(page, "lylanar_turlassil")

    assert len(guide.phases) == 1
    assert guide.phases[0].label == "Lylanar transition"
