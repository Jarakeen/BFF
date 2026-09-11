from __future__ import annotations

"""Audit Encounters / Boss Guide timeline and strategy coverage.

This tool is intentionally read-only. It reports whether each selectable encounter
has canonical boss-guide phases, reviewed evidence fallback timeline rows, and
reviewed strategy rows. It does not promote evidence or mutate encounter data.
"""

from dataclasses import dataclass
from pathlib import Path
import sys


# Support both ``python -m tools.audit_encounter_guide_coverage`` and direct
# ``python tools/audit_encounter_guide_coverage.py`` execution from the repo.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engine.config import get_data_dir
from services.encounter_boss_guide import EncounterBossGuideService
from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)
from services.encounter_identity_corrections import encounter_identity_is_excluded


@dataclass(frozen=True)
class EncounterGuideCoverageRow:
    encounter_id: str
    content_name: str
    encounter_name: str
    canonical_timeline_rows: int
    reviewed_timeline_rows: int
    strategy_rows: int

    @property
    def effective_timeline_source(self) -> str:
        if self.canonical_timeline_rows:
            return "canonical"
        if self.reviewed_timeline_rows:
            return "reviewed_fallback"
        return "missing"

    @property
    def timeline_missing(self) -> bool:
        return self.effective_timeline_source == "missing"

    @property
    def strategy_missing(self) -> bool:
        return self.strategy_rows == 0


def build_coverage_rows(data_root: Path) -> tuple[EncounterGuideCoverageRow, ...]:
    root = Path(data_root)
    guide_service = EncounterBossGuideService(root / "eso.db")
    projection_service = EncounterGuideEvidenceProjectionService(root)

    rows: list[EncounterGuideCoverageRow] = []
    for summary in guide_service.encounter_summaries():
        if encounter_identity_is_excluded(summary.content_id, summary.encounter_id):
            continue
        guide = guide_service.get(summary.encounter_id)
        projection = projection_service.get(summary.encounter_id, summary.name)
        rows.append(
            EncounterGuideCoverageRow(
                encounter_id=summary.encounter_id,
                content_name=summary.content_name or summary.content_id,
                encounter_name=summary.name,
                canonical_timeline_rows=len(guide.phases),
                reviewed_timeline_rows=len(projection.timeline),
                strategy_rows=len(projection.strategy),
            )
        )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row.content_name.casefold(),
                row.encounter_name.casefold(),
                row.encounter_id,
            ),
        )
    )


def _line(row: EncounterGuideCoverageRow) -> str:
    status = []
    if row.timeline_missing:
        status.append("MISSING TIMELINE")
    if row.strategy_missing:
        status.append("MISSING STRATEGY")
    status_text = ", ".join(status) if status else "covered"
    return (
        f"{row.content_name} | {row.encounter_name} | {row.encounter_id} | "
        f"timeline={row.effective_timeline_source} "
        f"(canonical={row.canonical_timeline_rows}, reviewed={row.reviewed_timeline_rows}) | "
        f"strategy={row.strategy_rows} | {status_text}"
    )


def main() -> int:
    rows = build_coverage_rows(get_data_dir())
    missing = tuple(row for row in rows if row.timeline_missing or row.strategy_missing)

    print("Encounter Guide Coverage Audit")
    print("==============================")
    print(f"Encounters checked: {len(rows)}")
    print(f"Encounters with timeline or strategy gaps: {len(missing)}")
    print()

    for row in missing:
        print(_line(row))

    if not missing:
        print("No timeline/strategy gaps found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
