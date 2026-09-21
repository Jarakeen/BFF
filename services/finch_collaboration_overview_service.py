from __future__ import annotations

"""Read-only Finch collaboration overview for FoundryDock.

The overview composes the existing Team, Raid Plan, Readiness, and Coverage shared
preview contracts. It adds no new authority and performs no local mutation.
"""

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.finch_shared_coverage_service import list_shared_coverage_from_finch
from services.finch_shared_import_service import (
    list_shared_raid_plans_from_finch,
    list_shared_teams_from_finch,
)
from services.finch_shared_provenance_service import format_shared_timestamp
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


@dataclass(frozen=True, slots=True)
class FinchCollaborationOverview:
    rows: tuple[FinchCollaborationRow, ...]
    errors: tuple[str, ...]


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def compose_collaboration_rows(
    *,
    teams=(),
    raid_plans=(),
    readiness=(),
    coverage=(),
) -> tuple[FinchCollaborationRow, ...]:
    rows: list[FinchCollaborationRow] = []

    for row in teams:
        focus = _clean(getattr(row, "current_focus", ""))
        summary = f"{int(getattr(row, 'member_count', 0) or 0)} member(s)"
        if focus:
            summary += f" • {focus}"
        rows.append(
            FinchCollaborationRow(
                kind="Team",
                item_name=_clean(getattr(row, "team_name", "")) or "(Unnamed Team)",
                publisher=_clean(getattr(row, "published_by", "")) or "Unknown",
                updated=format_shared_timestamp(getattr(row, "updated_at", "")),
                status=_clean(getattr(row, "provenance", "")) or "Not copied locally",
                summary=summary,
                route="roster_workspace",
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
        rows.append(
            FinchCollaborationRow(
                kind="Raid Plan",
                item_name=_clean(getattr(row, "name", "")) or "(Unnamed Raid Plan)",
                publisher=_clean(getattr(row, "published_by", "")) or "Unknown",
                updated=format_shared_timestamp(getattr(row, "updated_at", "")),
                status=_clean(getattr(row, "provenance", "")) or "Not copied locally",
                summary=summary,
                route="raid_plans",
            )
        )

    for row in readiness:
        total = int(getattr(row, "total", 0) or 0)
        human_ready = int(getattr(row, "human_ready", 0) or 0)
        build_gaps = int(getattr(row, "build_gaps", 0) or 0)
        coverage_gaps = int(getattr(row, "coverage_gaps", 0) or 0)
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
            )
        )

    for row in coverage:
        total = int(getattr(row, "total_effects", 0) or 0)
        covered = int(getattr(row, "covered", 0) or 0)
        missing = int(getattr(row, "missing", 0) or 0)
        attention = int(getattr(row, "needs_attention", 0) or 0)
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
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> FinchCollaborationOverview:
    root = Path(data_dir or get_data_dir())
    db_path = Path(database_path or DEFAULT_DATABASE)
    plans_path = Path(raid_plans_path or (root / "raid_plans.json"))

    errors: list[str] = []
    values: dict[str, tuple] = {}

    loaders = (
        (
            "Teams",
            lambda: list_shared_teams_from_finch(
                database_path=db_path,
                raid_plans_path=plans_path,
                settings_path=settings_path,
                timeout=timeout,
            ),
        ),
        (
            "Raid Plans",
            lambda: list_shared_raid_plans_from_finch(
                database_path=db_path,
                raid_plans_path=plans_path,
                settings_path=settings_path,
                timeout=timeout,
            ),
        ),
        (
            "Readiness",
            lambda: list_shared_readiness_from_finch(
                data_dir=root,
                database_path=db_path,
                settings_path=settings_path,
                timeout=timeout,
            ),
        ),
        (
            "Coverage",
            lambda: list_shared_coverage_from_finch(
                data_dir=root,
                database_path=db_path,
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

    return FinchCollaborationOverview(
        rows=compose_collaboration_rows(
            teams=values["Teams"],
            raid_plans=values["Raid Plans"],
            readiness=values["Readiness"],
            coverage=values["Coverage"],
        ),
        errors=tuple(errors),
    )


__all__ = [
    "FinchCollaborationOverview",
    "FinchCollaborationRow",
    "compose_collaboration_rows",
    "load_finch_collaboration_overview",
]
