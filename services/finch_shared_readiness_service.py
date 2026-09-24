from __future__ import annotations

"""Explicit FoundryDock <-> Finch shared readiness snapshots.

Readiness sharing is operational collaboration only. It publishes per-chair readiness
states that FoundryDock can currently prove plus explicit human-ready decisions. It
never publishes Personnel notes, run notes/events, local database ids, saved-build ids,
or private build details. Receiving shared readiness is read-only and never mutates
local readiness authority.
"""

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE, get_data_dir, get_settings_path, get_user_database_path
from models.raid_plan import RaidPlan
from services.finch_api_client import FinchApiClient, FinchSharedSnapshot
from services.raid_plan_repository import RaidPlanRepository
from services.raid_readiness_evidence_service import RaidReadinessEvidenceService
from services.raid_section_state_service import RaidSectionStateService
from services.settings_service import SettingsService


_SHARED_READINESS_SCHEMA_VERSION = 1


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def shared_readiness_payload(
    plan: RaidPlan,
    *,
    evidence_service: RaidReadinessEvidenceService,
    user_state: RaidSectionStateService,
) -> dict[str, object]:
    evidence = evidence_service.evaluate(plan)
    seats: list[dict[str, object]] = []

    build_ready = 0
    build_planned = 0
    build_gaps = 0
    assignment_ready = 0
    coverage_covered = 0
    coverage_gaps = 0
    human_ready_count = 0

    for member in plan.members:
        row = evidence.seat(member.seat_id)
        build_state = str(getattr(row, "build_state", "gap") or "gap")
        build_label = _clean(getattr(row, "build_label", ""))
        coverage_state = str(
            getattr(row, "coverage_state", "not_applicable") or "not_applicable"
        )
        coverage_label = _clean(getattr(row, "coverage_label", ""))
        assignment_ok = bool(member.primary_assignment or member.secondary_assignment)
        human_ready = user_state.human_ready(plan.plan_id, member.seat_id)

        if build_state == "ready":
            build_ready += 1
        elif build_state == "planned":
            build_planned += 1
        else:
            build_gaps += 1
        if assignment_ok:
            assignment_ready += 1
        if coverage_state == "covered":
            coverage_covered += 1
        elif coverage_state == "gap":
            coverage_gaps += 1
        if human_ready is True:
            human_ready_count += 1

        seats.append(
            {
                "seat_id": member.seat_id,
                "gamertag": member.gamertag,
                "character_name": member.character_name or "",
                "role": member.role or "",
                "build_state": build_state,
                "build_label": build_label,
                "assignment_ready": assignment_ok,
                "coverage_state": coverage_state,
                "coverage_label": coverage_label,
                "human_ready": human_ready,
            }
        )

    total = len(plan.members)
    return {
        "plan_id": plan.plan_id,
        "name": plan.name,
        "trial_id": plan.trial_id,
        "team_name": plan.team_name or "",
        "difficulty": plan.difficulty or "",
        "summary": {
            "total": total,
            "build_ready": build_ready,
            "build_planned": build_planned,
            "build_gaps": build_gaps,
            "assignment_ready": assignment_ready,
            "coverage_covered": coverage_covered,
            "coverage_gaps": coverage_gaps,
            "human_ready": human_ready_count,
            "human_pending": max(0, total - human_ready_count),
        },
        "seats": seats,
    }


@dataclass(frozen=True, slots=True)
class FinchReadinessPublishResult:
    snapshot_key: str
    published_by: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class FinchSharedReadinessPreview:
    snapshot_key: str
    plan_id: str
    name: str
    trial_id: str
    team_name: str
    difficulty: str
    total: int
    build_ready: int
    build_planned: int
    build_gaps: int
    assignment_ready: int
    coverage_covered: int
    coverage_gaps: int
    human_ready: int
    human_pending: int
    published_by: str
    updated_at: str


class FinchSharedReadinessService:
    def __init__(
        self,
        *,
        client: FinchApiClient,
        evidence_service: RaidReadinessEvidenceService,
        user_state: RaidSectionStateService,
    ) -> None:
        self.client = client
        self.evidence_service = evidence_service
        self.user_state = user_state

    @staticmethod
    def preview(snapshot: FinchSharedSnapshot) -> FinchSharedReadinessPreview:
        if snapshot.kind != "readiness":
            raise ValueError(
                f"Expected Finch shared 'readiness' snapshot, got {snapshot.kind!r}."
            )
        if snapshot.schema_version != _SHARED_READINESS_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported Finch shared readiness schema version: "
                f"{snapshot.schema_version}"
            )
        body = snapshot.payload
        summary = body.get("summary")
        if not isinstance(summary, dict):
            summary = {}

        def count(name: str) -> int:
            try:
                return max(0, int(summary.get(name) or 0))
            except (TypeError, ValueError):
                return 0

        return FinchSharedReadinessPreview(
            snapshot_key=snapshot.snapshot_key,
            plan_id=_clean(body.get("plan_id")),
            name=_clean(body.get("name")),
            trial_id=_clean(body.get("trial_id")),
            team_name=_clean(body.get("team_name")),
            difficulty=_clean(body.get("difficulty")),
            total=count("total"),
            build_ready=count("build_ready"),
            build_planned=count("build_planned"),
            build_gaps=count("build_gaps"),
            assignment_ready=count("assignment_ready"),
            coverage_covered=count("coverage_covered"),
            coverage_gaps=count("coverage_gaps"),
            human_ready=count("human_ready"),
            human_pending=count("human_pending"),
            published_by=snapshot.published_by,
            updated_at=snapshot.updated_at,
        )

    def publish(self, plan: RaidPlan) -> FinchReadinessPublishResult:
        payload = shared_readiness_payload(
            plan,
            evidence_service=self.evidence_service,
            user_state=self.user_state,
        )
        snapshot = self.client.publish_shared_readiness(
            snapshot_key=plan.plan_id,
            payload=payload,
            schema_version=_SHARED_READINESS_SCHEMA_VERSION,
        )
        return FinchReadinessPublishResult(
            snapshot_key=snapshot.snapshot_key,
            published_by=snapshot.published_by,
            updated_at=snapshot.updated_at,
        )

    def list_shared(self) -> tuple[FinchSharedReadinessPreview, ...]:
        return tuple(
            self.preview(snapshot)
            for snapshot in self.client.shared_readiness_snapshots()
        )

    def get_shared(self, snapshot_key: str) -> FinchSharedReadinessPreview:
        return self.preview(self.client.shared_readiness(snapshot_key))


def _configured_client(
    *,
    settings_path: Path,
    timeout: float,
) -> FinchApiClient:
    settings = SettingsService(Path(settings_path)).load()
    return FinchApiClient(
        base_url=str(settings.get("FinchApiUrl") or ""),
        api_key=str(settings.get("FinchApiKey") or ""),
        timeout=timeout,
    )


def _service(
    *,
    data_dir: Path,
    database_path: Path,
    settings_path: Path,
    timeout: float,
    state_path: Path | None = None,
) -> FinchSharedReadinessService:
    return FinchSharedReadinessService(
        client=_configured_client(settings_path=settings_path, timeout=timeout),
        evidence_service=RaidReadinessEvidenceService(
            data_dir=data_dir,
            database_path=database_path,
        ),
        user_state=RaidSectionStateService(state_path),
    )


def publish_readiness_to_finch(
    *,
    plan_id: str,
    raid_plans_path: Path | None = None,
    data_dir: Path | None = None,
    database_path: Path | None = None,
    settings_path: Path = get_settings_path(),
    state_path: Path | None = None,
    timeout: float = 10.0,
) -> FinchReadinessPublishResult:
    root = Path(data_dir or get_data_dir())
    plans = RaidPlanRepository(Path(raid_plans_path) if raid_plans_path is not None else get_user_database_path())
    plan = plans.get(plan_id)
    if plan is None:
        raise ValueError(f"Saved Raid Plan {plan_id!r} does not exist.")
    return _service(
        data_dir=root,
        database_path=Path(database_path or DEFAULT_DATABASE),
        settings_path=settings_path,
        timeout=timeout,
        state_path=state_path,
    ).publish(plan)


def list_shared_readiness_from_finch(
    *,
    data_dir: Path | None = None,
    database_path: Path | None = None,
    settings_path: Path = get_settings_path(),
    state_path: Path | None = None,
    timeout: float = 10.0,
) -> tuple[FinchSharedReadinessPreview, ...]:
    root = Path(data_dir or get_data_dir())
    return _service(
        data_dir=root,
        database_path=Path(database_path or DEFAULT_DATABASE),
        settings_path=settings_path,
        timeout=timeout,
        state_path=state_path,
    ).list_shared()


__all__ = [
    "FinchReadinessPublishResult",
    "FinchSharedReadinessPreview",
    "FinchSharedReadinessService",
    "list_shared_readiness_from_finch",
    "publish_readiness_to_finch",
    "shared_readiness_payload",
]
