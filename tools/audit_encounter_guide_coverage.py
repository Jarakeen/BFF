from __future__ import annotations

"""Audit Encounters / Boss Guide timeline and strategy coverage.

This tool is intentionally read-only. The default scope is the reviewed raid-planning
encounter registry, where raw NPC/source records are grouped into the fight units a
raid lead actually plans. ``--dungeons`` audits the reviewed dungeon-planning registry
in newest-first release order. ``--raw-trial-records`` audits all raw records under
known trial content; ``--all-content`` audits the full dungeon/arena/source corpus.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engine.config import get_data_dir
from services.dungeon_encounter_identity_service import load_dungeon_encounter_identities
from services.encounter_boss_guide import (
    EncounterBossGuideError,
    EncounterBossGuideNotFound,
    EncounterBossGuideService,
)
from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)
from services.encounter_identity_corrections import encounter_identity_is_excluded
from services.esologs_client import KNOWN_TRIAL_ZONE_NAMES
from services.raid_encounter_identity_service import load_raid_encounter_identities


@dataclass(frozen=True)
class EncounterGuideCoverageRow:
    encounter_id: str
    content_name: str
    encounter_name: str
    canonical_timeline_rows: int | None
    reviewed_timeline_rows: int
    strategy_rows: int
    release_year: int | None = None
    release_update: int | None = None

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


def _canonical_phase_count(
    guide_service: EncounterBossGuideService,
    member_ids: tuple[str, ...],
) -> int | None:
    """Return canonical phase rows, or None when canonical persistence is unavailable.

    Reviewed raid/dungeon audits have an independent reviewed-evidence fallback, so a
    missing or schema-incompatible canonical encounter database must not prevent those
    scopes from auditing that reviewed material. ``None`` preserves the distinction
    between "canonical data was available and contained no timeline" and "canonical
    persistence could not be read". Raw database audit scopes still call the guide
    service directly and therefore continue to fail closed when persistence is invalid.
    """
    total = 0
    for member_id in member_ids:
        try:
            total += len(guide_service.get(member_id).phases)
        except EncounterBossGuideNotFound:
            continue
        except EncounterBossGuideError:
            return None
    return total


def _reviewed_raid_rows(data_root: Path) -> tuple[EncounterGuideCoverageRow, ...]:
    root = Path(data_root)
    guide_service = EncounterBossGuideService(root / "eso.db")
    projection_service = EncounterGuideEvidenceProjectionService(root)
    rows: list[EncounterGuideCoverageRow] = []

    for identity in load_raid_encounter_identities(root):
        projection = projection_service.get(identity.encounter_id, identity.display_name)
        rows.append(
            EncounterGuideCoverageRow(
                encounter_id=identity.encounter_id,
                content_name=identity.content_name,
                encounter_name=identity.display_name,
                canonical_timeline_rows=_canonical_phase_count(
                    guide_service, identity.member_ids
                ),
                reviewed_timeline_rows=len(projection.timeline),
                strategy_rows=len(projection.strategy),
            )
        )
    return tuple(rows)


def _reviewed_dungeon_rows(data_root: Path) -> tuple[EncounterGuideCoverageRow, ...]:
    root = Path(data_root)
    guide_service = EncounterBossGuideService(root / "eso.db")
    projection_service = EncounterGuideEvidenceProjectionService(root)
    rows: list[EncounterGuideCoverageRow] = []

    for identity in load_dungeon_encounter_identities(root):
        projection = projection_service.get(identity.encounter_id, identity.display_name)
        rows.append(
            EncounterGuideCoverageRow(
                encounter_id=identity.encounter_id,
                content_name=identity.content_name,
                encounter_name=identity.display_name,
                canonical_timeline_rows=_canonical_phase_count(
                    guide_service, identity.member_ids
                ),
                reviewed_timeline_rows=len(projection.timeline),
                strategy_rows=len(projection.strategy),
                release_year=identity.release_year,
                release_update=identity.release_update,
            )
        )
    return tuple(rows)


def _raw_rows(
    data_root: Path,
    *,
    trials_only: bool,
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
    return tuple(rows)


def build_coverage_rows(
    data_root: Path,
    *,
    scope: str = "raid",
) -> tuple[EncounterGuideCoverageRow, ...]:
    if scope == "raid":
        rows = _reviewed_raid_rows(data_root)
    elif scope == "dungeon":
        rows = _reviewed_dungeon_rows(data_root)
    elif scope == "raw_trials":
        rows = _raw_rows(data_root, trials_only=True)
    elif scope == "all":
        rows = _raw_rows(data_root, trials_only=False)
    else:
        raise ValueError(f"unsupported encounter guide audit scope {scope!r}")

    if scope == "dungeon":
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    -(row.release_year or 0),
                    -(row.release_update or 0),
                    row.content_name.casefold(),
                    row.encounter_name.casefold(),
                    row.encounter_id,
                ),
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
    canonical_text = (
        "unavailable"
        if row.canonical_timeline_rows is None
        else str(row.canonical_timeline_rows)
    )
    return (
        f"{row.content_name} | {row.encounter_name} | {row.encounter_id} | "
        f"timeline={row.effective_timeline_source} "
        f"(canonical={canonical_text}, reviewed={row.reviewed_timeline_rows}) | "
        f"strategy={row.strategy_rows} | {status_text}"
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Encounter Guide timeline and strategy coverage."
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--dungeons",
        action="store_true",
        help="Audit reviewed dungeon encounters newest-first by release update.",
    )
    scope.add_argument(
        "--raw-trial-records",
        action="store_true",
        help="Audit every raw source record under known trial content.",
    )
    scope.add_argument(
        "--all-content",
        action="store_true",
        help="Audit dungeons, arenas, trials, and all other persisted source records.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    scope = (
        "dungeon"
        if args.dungeons
        else "all"
        if args.all_content
        else "raw_trials"
        if args.raw_trial_records
        else "raid"
    )
    rows = build_coverage_rows(get_data_dir(), scope=scope)
    missing = tuple(row for row in rows if row.timeline_missing or row.strategy_missing)

    scope_label = {
        "raid": "reviewed raid encounters",
        "dungeon": "reviewed dungeon encounters (newest first)",
        "raw_trials": "raw known-trial records",
        "all": "all content",
    }[scope]
    print("Encounter Guide Coverage Audit")
    print("==============================")
    print(f"Scope: {scope_label}")
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
