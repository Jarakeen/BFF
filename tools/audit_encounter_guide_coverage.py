from __future__ import annotations

"""Audit Encounters / Boss Guide timeline and strategy coverage.

This tool is intentionally read-only. It reports whether each selectable encounter
has canonical boss-guide phases, reviewed evidence fallback timeline rows, and
reviewed strategy rows. It does not promote evidence or mutate encounter data.

Raid Engine work defaults to known trial content. Pass ``--all-content`` to audit
the broader dungeon/arena/source corpus as well.
"""

import argparse
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
from services.esologs_client import KNOWN_TRIAL_ZONE_NAMES


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


def _content_key(value: str) -> str:
    text = str(value or "").strip().casefold()
    if text.startswith("the "):
        text = text[4:]
    return text


def _known_trial_content_names() -> frozenset[str]:
    return frozenset(_content_key(name) for name in KNOWN_TRIAL_ZONE_NAMES)


def _include_content(content_name: str, *, trials_only: bool) -> bool:
    if not trials_only:
        return True
    return _content_key(content_name) in _known_trial_content_names()


def build_coverage_rows(
    data_root: Path,
    *,
    trials_only: bool = True,
) -> tuple[EncounterGuideCoverageRow, ...]:
    root = Path(data_root)
    guide_service = EncounterBossGuideService(root / "eso.db")
    projection_service = EncounterGuideEvidenceProjectionService(root)

    rows: list[EncounterGuideCoverageRow] = []
    for summary in guide_service.encounter_summaries():
        if encounter_identity_is_excluded(summary.content_id, summary.encounter_id):
            continue
        content_name = summary.content_name or summary.content_id
        if not _include_content(content_name, trials_only=trials_only):
            continue
        guide = guide_service.get(summary.encounter_id)
        projection = projection_service.get(summary.encounter_id, summary.name)
        rows.append(
            EncounterGuideCoverageRow(
                encounter_id=summary.encounter_id,
                content_name=content_name,
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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Encounter Guide timeline and strategy coverage."
    )
    parser.add_argument(
        "--all-content",
        action="store_true",
        help="Include dungeons, arenas, and other source content. Default is known trials only.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    trials_only = not args.all_content
    rows = build_coverage_rows(get_data_dir(), trials_only=trials_only)
    missing = tuple(row for row in rows if row.timeline_missing or row.strategy_missing)

    print("Encounter Guide Coverage Audit")
    print("==============================")
    print(f"Scope: {'known trials' if trials_only else 'all content'}")
    print(f"Encounter rows checked: {len(rows)}")
    print(f"Rows with timeline or strategy gaps: {len(missing)}")
    print()

    for row in missing:
        print(_line(row))

    if not missing:
        print("No timeline/strategy gaps found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
