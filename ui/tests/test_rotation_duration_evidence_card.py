from PySide6.QtWidgets import QApplication

from ui.components.rotation_duration_evidence_card import RotationDurationEvidenceCard
from ui.rotation_duration_evidence_support import (
    RotationDurationEvidence,
    RotationDurationEvidenceRow,
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _evidence() -> RotationDurationEvidence:
    return RotationDurationEvidence(
        rows=(
            RotationDurationEvidenceRow(
                ability="Radiating Regeneration",
                bar="Front",
                duration_seconds=10.0,
                casts=4,
                uptime_percent=96.7,
                gap_seconds=2.0,
                premature_seconds=1.0,
            ),
        ),
        summary="Verified duration rules: 1 • Average projected uptime: 96.7%",
        detail="Total uncovered gap: 2.0s • Premature overlap: 1.0s • Unresolved duration evidence: 0",
        unresolved=(),
    )


def test_duration_evidence_card_renders_rows() -> None:
    _app()
    card = RotationDurationEvidenceCard()

    card.set_evidence(_evidence())

    assert "Verified duration rules: 1" in card.summary_label.text()
    assert card.table.rowCount() == 1
    assert card.table.item(0, 0).text() == "Front"
    assert card.table.item(0, 1).text() == "Radiating Regeneration"
    assert card.table.item(0, 2).text() == "10s"
    assert card.table.item(0, 4).text() == "96.7%"
    assert card.table.item(0, 5).text() == "2.0s"
    assert card.table.item(0, 6).text() == "1.0s"


def test_duration_evidence_card_clears() -> None:
    _app()
    card = RotationDurationEvidenceCard()
    card.set_evidence(_evidence())

    card.clear_evidence()

    assert card.table.rowCount() == 0
    assert card.summary_label.text() == "No duration evidence generated yet."
