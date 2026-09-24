from __future__ import annotations

"""Read-only Finch collaboration overview for FoundryDock.

The overview composes the existing Team, Raid Plan, Readiness, and Coverage shared
preview contracts. It adds no new authority and performs no local mutation.
"""

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE, get_data_dir, get_settings_path, get_user_database_path
from services.finch_shared_coverage_service import list_shared_coverage_from_finch
from services.finch_shared_import_service import (
    list_shared_raid_plans_from_finch,
    list_shared_teams_from_finch,
)
from services.finch_shared_provenance_service import (
    FinchSharedProvenanceService,
    format_shared_timestamp,
)
from services.finch_shared_readiness_service import list_shared_readiness_from_finch


@dataclass(frozen=True, slots=True)
class FinchCollaborationRow:
    kind: str
    item_name: str
    publisher: str
    updated: str
    status: str
    summary: str
    route: str
    context_key: str = ""
    attention_tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FinchCollaborationAttentionSummary:
    changed: int = 0
    not_copied: int = 0
    readiness_gaps: int = 0
    coverage_gaps: int = 0

    @property
    def total_attention(self) -> int:
        return self.changed + self.not_copied + self.readiness_gaps + self.coverage_gaps


@dataclass(frozen=True, slots=True)
class FinchCollaborationOverview:
    rows: tuple[FinchCollaborationRow, ...]
    errors: tuple[str, ...]
    attention: FinchCollaborationAttentionSummary


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def compose_collaboration_rows(
    *,
    teams=(),
    raid_plans=(),
    readiness=(),
    coverage=(),
    provenance: FinchSharedProvenanceService | None = None,
) -> tuple[FinchCollaborationRow, ...]:
    rows: list[FinchCollaborationRow] = []

    for row in teams:
        focus = _clean(getattr(row, "current_focus", ""))
        summary = f"{int(getattr(row, 'member_count', 0) or 0)} member(s)"
        if focus:
            summary += f" • {focus}"
        copy_status = _clean(getattr(row, "provenance", "")) or "Not copied locally"
        tags = []
        if copy_status.startswith("Updated on Finch since copy"):
            tags.append("changed")
        if copy_status == "Not copied locally":
            tags.append("not_copied")
        rows.append(
            FinchCollaborationRow(
                kind="Team",
                item_name=_clean(getattr(row, "team_name", "")) or "(Unnamed Team)",
                publisher=_clean(getattr(row, "published_by", "")) or "Unknown",
                updated=format_shared_timestamp(getattr(row, "updated_at", "")),
                status=copy_status,
                summary=summary,
                route="roster_workspace",
                context_key=_clean(getattr(row, "local_key", "")),
                attention_tags=tuple(tags),
            )
        )

    for row in raid_plans:
        summary = (
            f"{_clean(getattr(row, 'trial_id', '')) or 'Trial unknown'} • "
            f"{int(getattr(row, 'member_count', 0) or 0)} seat(s)"
        )
        team_name = _clean(getattr(row, "team_name", ""))
        if team_name:
            summary += f" • {team_name}"
        copy_status = _clean(getattr(row, "provenance", "")) or "Not copied locally"
        tags = []
        if copy_status.startswith("Updated on Finch since copy"):
            tags.append("changed")
        if copy_status == "Not copied locally":
            tags.append("not_copied")
        rows.append(
            FinchCollaborationRow(
                kind="Raid Plan",
                item_name=_clean(getattr(row, "name", "")) or "(Unnamed Raid Plan)",
                publisher=_clean(getattr(row, "published_by", "")) or "Unknown",
                updated=format_shared_timestamp(getattr(row, "updated_at", "")),
                status=copy_status,
                summary=summary,
                route="raid_plans",
                context_key=_clean(getattr(row, "local_key", "")),
                attention_tags=tuple(tags),
            )
        )

    for row in readiness:
        total = int(getattr(row, "total", 0) or 0)
        human_ready = int(getattr(row, "human_ready", 0) or 0)
        build_gaps = int(getattr(row, "build_gaps", 0) or 0)
        coverage_gaps = int(getattr(row, "coverage_gaps", 0) or 0)
        human_pending = max(0, total - human_ready)
        tags = ("readiness_gaps",) if (build_gaps or coverage_gaps or human_pending) else ()
        local_copy = (
            provenance.latest_copy_for(
                kind="raid_plan",
                snapshot_key=_clean(getattr(row, "snapshot_key", ""))
                or _clean(getattr(row, "plan_id", "")),
            )
            if provenance is not None
            else None
        )
        rows.append(
            FinchCollaborationRow(
                kind="Readiness",
                item_name=_clean(getattr(row, "name", "")) or _clean(getattr(row, "plan_id", "")) or "(Unnamed Plan)",
                publisher=_clean(getattr(row, "published_by", "")) or "Unknown",
                updated=format_shared_timestamp(getattr(row, "updated_at", "")),
                status="Read-only snapshot",
                summary=(
                    f"{human_ready}/{total} human ready • "
                    f"{build_gaps} build gap(s) • {coverage_gaps} coverage gap(s)"
                ),
                route="readiness",
                context_key=local_copy.local_key if local_copy is not None else "",
                attention_tags=tags,
            )
        )

    for row in coverage:
        total = int(getattr(row, "total_effects", 0) or 0)
        covered = int(getattr(row, "covered", 0) or 0)
        missing = int(getattr(row, "missing", 0) or 0)
        attention = int(getattr(row, "needs_attention", 0) or 0)
        duplicates = int(getattr(row, "duplicate_primary", 0) or 0)
        unresolved = int(getattr(row, "unresolved_chairs", 0) or 0)
        tags = ("coverage_gaps",) if (missing or attention or duplicates or unresolved) else ()
        local_copy = (
            provenance.latest_copy_for(
                kind="raid_plan",
                snapshot_key=_clean(getattr(row, "snapshot_key", ""))
                or _clean(getattr(row, "plan_id", "")),
            )
            if provenance is not None
            else None
        )
        rows.append(
            FinchCollaborationRow(
                kind="Coverage",
                item_name=_clean(getattr(row, "name", "")) or _clean(getattr(row, "plan_id", "")) or "(Unnamed Plan)",
                publisher=_clean(getattr(row, "published_by", "")) or "Unknown",
                updated=format_shared_timestamp(getattr(row, "updated_at", "")),
                status="Read-only snapshot",
                summary=(
                    f"{covered}/{total} covered • {missing} missing • "
                    f"{attention} need attention"
                ),
                route="console:7",
                context_key=local_copy.local_key if local_copy is not None else "",
                attention_tags=tags,
            )
        )

    kind_order = {"Team": 0, "Raid Plan": 1, "Readiness": 2, "Coverage": 3}
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                kind_order.get(row.kind, 99),
                row.item_name.casefold(),
                row.publisher.casefold(),
            ),
        )
    )


def load_finch_collaboration_overview(
    *,
    data_dir: Path | None = None,
    database_path: Path | None = None,
    raid_plans_path: Path | None = None,
    settings_path: Path = get_settings_path(),
    timeout: float = 10.0,
) -> FinchCollaborationOverview:
    root = Path(data_dir or get_data_dir())
    reference_db_path = Path(database_path or DEFAULT_DATABASE)
    user_db_path = get_user_database_path()
    plans_path = Path(raid_plans_path or user_db_path)

    errors: list[str] = []
    values: dict[str, tuple] = {}

    loaders = (
        (
            "Teams",
            lambda: list_shared_teams_from_finch(
                database_path=user_db_path,
                raid_plans_path=plans_path,
                settings_path=settings_path,
                timeout=timeout,
            ),
        ),
        (
            "Raid Plans",
            lambda: list_shared_raid_plans_from_finch(
                database_path=user_db_path,
                raid_plans_path=plans_path,
                settings_path=settings_path,
                timeout=timeout,
            ),
        ),
        (
            "Readiness",
            lambda: list_shared_readiness_from_finch(
                data_dir=root,
                database_path=reference_db_path,
                settings_path=settings_path,
                timeout=timeout,
            ),
        ),
        (
            "Coverage",
            lambda: list_shared_coverage_from_finch(
                data_dir=root,
                database_path=reference_db_path,
                settings_path=settings_path,
                timeout=timeout,
            ),
        ),
    )

    for label, loader in loaders:
        try:
            values[label] = tuple(loader())
        except Exception as exc:
            values[label] = ()
            errors.append(f"{label}: {type(exc).__name__}: {exc}")

    provenance = FinchSharedProvenanceService(
        plans_path.parent / "finch_shared_provenance.json"
    )
    rows = compose_collaboration_rows(
        teams=values["Teams"],
        raid_plans=values["Raid Plans"],
        readiness=values["Readiness"],
        coverage=values["Coverage"],
        provenance=provenance,
    )
    attention = FinchCollaborationAttentionSummary(
        changed=sum("changed" in row.attention_tags for row in rows),
        not_copied=sum("not_copied" in row.attention_tags for row in rows),
        readiness_gaps=sum("readiness_gaps" in row.attention_tags for row in rows),
        coverage_gaps=sum("coverage_gaps" in row.attention_tags for row in rows),
    )
    return FinchCollaborationOverview(
        rows=rows,
        errors=tuple(errors),
        attention=attention,
    )


__all__ = [
    "FinchCollaborationAttentionSummary",
    "FinchCollaborationOverview",
    "FinchCollaborationRow",
    "compose_collaboration_rows",
    "load_finch_collaboration_overview",
]
