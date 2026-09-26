from pathlib import Path

import pytest

from models.raid_plan import RaidPlan
from services.coverage_pdf_export_service import CoveragePDFRow, export_coverage_pdf


def _plan() -> RaidPlan:
    return RaidPlan(
        plan_id="sunspire-performance-mode-gs",
        trial_id="sunspire",
        name="Godslayer Performance Mode",
        team_name="Performance Mode",
        difficulty="Veteran Hardmode",
    )


def test_coverage_pdf_export_writes_printer_friendly_packet(tmp_path: Path) -> None:
    target = tmp_path / "coverage.pdf"
    rows = (
        CoveragePDFRow(
            effect="Minor Berserk",
            provider="MrsPoeguine",
            backup="Jarakeen",
            source="Combat Prayer",
            status="Covered • Supported",
        ),
        CoveragePDFRow(
            effect="Major Slayer",
            provider="ImJadedBabe",
            backup="—",
            source="War Machine",
            status="Covered • Conditional",
        ),
    )

    result = export_coverage_pdf(_plan(), rows, target)

    assert result == target
    assert target.read_bytes().startswith(b"%PDF")
    assert target.stat().st_size > 1000


def test_coverage_pdf_row_requires_effect_name() -> None:
    with pytest.raises(ValueError, match="requires an effect"):
        CoveragePDFRow(
            effect="",
            provider="Jarakeen",
            backup="",
            source="Master Architect",
            status="Covered",
        )


def test_coverage_pdf_rejects_noncanonical_rows(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="CoveragePDFRow"):
        export_coverage_pdf(_plan(), (object(),), tmp_path / "bad.pdf")
