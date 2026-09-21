from __future__ import annotations

"""Explicit FoundryDock <-> Finch shared Coverage snapshots.

Coverage sharing publishes raid-planning evidence only. It reuses the same canonical
RaidPlan scope, saved-build capability, planned-gear/skill overlays, and assignment
review services as the Coverage UI. It never publishes local ids, notes, private URLs,
or runtime combat telemetry. Receiving shared Coverage is read-only.
"""

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE, get_data_dir
from models.raid_plan import RaidPlan
from services.build_service import BuildService
from services.finch_api_client import FinchApiClient, FinchSharedSnapshot
from services.raid_group_effect_catalog import (
    GROUP_COVERAGE_BY_NAME,
    GROUP_COVERAGE_NAMES,
)
from services.raid_named_group_effect_capability_service import (
    RaidNamedGroupEffectCapabilityService,
)
from services.raid_plan_coverage_assignment_service import (
    RaidPlanCoverageAssignmentService,
)
from services.raid_plan_coverage_scope_service import RaidPlanCoverageScopeService
from services.raid_plan_repository import RaidPlanRepository
from services.raid_planned_gear_coverage_service import (
    PlannedGearCoverageProvider,
    RaidPlannedGearCoverageService,
)
from services.raid_planned_skill_coverage_service import (
    PlannedSkillCoverageProvider,
    RaidPlannedSkillCoverageService,
)
from services.raid_unique_support_set_capability_service import (
    RaidUniqueSupportSetCapabilityService,
)
from services.raid_unique_support_set_catalog import (
    UNIQUE_SUPPORT_SET_BY_NAME,
    UNIQUE_SUPPORT_SET_NAMES,
)
from services.saved_build_capability_service import (
    RaidCoverageSnapshot,
    SavedBuildCapabilityService,
    summarize_raid_coverage,
)
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from services.settings_service import SettingsService


_SHARED_COVERAGE_SCHEMA_VERSION = 1
COVERAGE_NAMES = tuple(
    dict.fromkeys((*GROUP_COVERAGE_NAMES, *UNIQUE_SUPPORT_SET_NAMES))
)
REFERENCE_BY_NAME = {**GROUP_COVERAGE_BY_NAME, **UNIQUE_SUPPORT_SET_BY_NAME}


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _extend_snapshot(snapshot: RaidCoverageSnapshot) -> RaidCoverageSnapshot:
    status = {name: "unverified" for name in COVERAGE_NAMES}
    providers = {name: [] for name in COVERAGE_NAMES}
    conditional = {name: [] for name in COVERAGE_NAMES}
    for name in COVERAGE_NAMES:
        if name in snapshot.status:
            status[name] = snapshot.status[name]
        if name in snapshot.providers:
            providers[name] = list(snapshot.providers[name])
        if name in snapshot.conditional_providers:
            conditional[name] = list(snapshot.conditional_providers[name])
    return RaidCoverageSnapshot(status, providers, conditional)


def _coverage_snapshot(
    plan: RaidPlan,
    *,
    build_service: BuildService,
    database_path: Path,
):
    saved_builds = tuple(build_service.load().Members)
    scope = RaidPlanCoverageScopeService().compose(
        raid_plan=plan,
        saved_builds=saved_builds,
        coverage_effect_names=COVERAGE_NAMES,
        total_chairs=len(plan.members),
    )
    capability_service = SavedBuildCapabilityService(build_service, database_path)
    audits = [
        (row.build, capability_service.audit_build(row.build))
        for row in scope.members
    ]
    snapshot = _extend_snapshot(
        summarize_raid_coverage(DEFAULT_RAID_COVERAGE_PROFILE, audits)
    )
    snapshot = RaidNamedGroupEffectCapabilityService().overlay(
        snapshot,
        scope.resolved_builds,
        capability_service=capability_service,
    )
    snapshot = RaidUniqueSupportSetCapabilityService().overlay(
        snapshot,
        scope.resolved_builds,
    )
    snapshot = RaidPlannedGearCoverageService(database_path).overlay(
        snapshot,
        tuple(
            PlannedGearCoverageProvider(
                seat_id=row.seat_id,
                provider_label=row.player_label,
                gear_sets=row.gear_sets,
            )
            for row in scope.planned_gear
        ),
        effect_names=COVERAGE_NAMES,
    )
    snapshot = RaidPlannedSkillCoverageService(database_path).overlay(
        snapshot,
        tuple(
            PlannedSkillCoverageProvider(
                seat_id=row.seat_id,
                provider_label=row.player_label,
                eso_class=row.eso_class,
                skills=row.skills,
            )
            for row in scope.planned_skills
        ),
        effect_names=COVERAGE_NAMES,
    )
    return scope, snapshot


def shared_coverage_payload(
    plan: RaidPlan,
    *,
    build_service: BuildService,
    database_path: Path,
) -> dict[str, object]:
    scope, snapshot = _coverage_snapshot(
        plan,
        build_service=build_service,
        database_path=database_path,
    )
    assignment_service = RaidPlanCoverageAssignmentService()
    effects: list[dict[str, object]] = []
    covered = 0
    missing = 0
    needs_attention = 0
    duplicate_primary = 0

    for effect_name in COVERAGE_NAMES:
        review = assignment_service.review(
            effect_name=effect_name,
            scope=scope,
            snapshot=snapshot,
        )
        if review.counts_as_planned_coverage:
            covered += 1
        else:
            missing += 1
        if review.needs_attention:
            needs_attention += 1
        if review.duplicate_primary:
            duplicate_primary += 1

        reference = REFERENCE_BY_NAME.get(effect_name)
        effects.append(
            {
                "effect_name": effect_name,
                "required": bool(
                    reference is not None
                    and getattr(reference, "default_required", False)
                ),
                "coverage_state": review.coverage_state,
                "evidence_state": review.state,
                "label": review.label,
                "primary": list(review.primary),
                "backup": list(review.backup),
                "static_providers": list(snapshot.providers.get(effect_name, ()) or ()),
                "conditional_providers": list(
                    snapshot.conditional_providers.get(effect_name, ()) or ()
                ),
                "duplicate_primary": bool(review.duplicate_primary),
                "needs_attention": bool(review.needs_attention),
            }
        )

    return {
        "plan_id": plan.plan_id,
        "name": plan.name,
        "trial_id": plan.trial_id,
        "team_name": plan.team_name or "",
        "difficulty": plan.difficulty or "",
        "summary": {
            "total_effects": len(COVERAGE_NAMES),
            "covered": covered,
            "missing": missing,
            "needs_attention": needs_attention,
            "duplicate_primary": duplicate_primary,
            "unresolved_chairs": len(scope.unresolved),
        },
        "effects": effects,
    }


@dataclass(frozen=True, slots=True)
class FinchSharedCoverageEffect:
    effect_name: str
    required: bool
    coverage_state: str
    evidence_state: str
    label: str
    primary: tuple[str, ...]
    backup: tuple[str, ...]
    static_providers: tuple[str, ...]
    conditional_providers: tuple[str, ...]
    duplicate_primary: bool
    needs_attention: bool


@dataclass(frozen=True, slots=True)
class FinchSharedCoveragePreview:
    snapshot_key: str
    plan_id: str
    name: str
    trial_id: str
    team_name: str
    difficulty: str
    total_effects: int
    covered: int
    missing: int
    needs_attention: int
    duplicate_primary: int
    unresolved_chairs: int
    effects: tuple[FinchSharedCoverageEffect, ...]
    published_by: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class FinchCoveragePublishResult:
    snapshot_key: str
    published_by: str
    updated_at: str


class FinchSharedCoverageService:
    def __init__(
        self,
        *,
        client: FinchApiClient,
        build_service: BuildService,
        database_path: Path,
    ) -> None:
        self.client = client
        self.build_service = build_service
        self.database_path = Path(database_path)

    @staticmethod
    def preview(snapshot: FinchSharedSnapshot) -> FinchSharedCoveragePreview:
        if snapshot.kind != "coverage":
            raise ValueError(
                f"Expected Finch shared 'coverage' snapshot, got {snapshot.kind!r}."
            )
        if snapshot.schema_version != _SHARED_COVERAGE_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported Finch shared Coverage schema version: "
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

        rows: list[FinchSharedCoverageEffect] = []
        raw_effects = body.get("effects")
        if isinstance(raw_effects, list):
            for raw in raw_effects:
                if not isinstance(raw, dict):
                    continue
                def values(key: str) -> tuple[str, ...]:
                    source = raw.get(key)
                    if not isinstance(source, list):
                        return ()
                    return tuple(
                        _clean(value) for value in source if _clean(value)
                    )

                rows.append(
                    FinchSharedCoverageEffect(
                        effect_name=_clean(raw.get("effect_name")),
                        required=bool(raw.get("required")),
                        coverage_state=_clean(raw.get("coverage_state")),
                        evidence_state=_clean(raw.get("evidence_state")),
                        label=_clean(raw.get("label")),
                        primary=values("primary"),
                        backup=values("backup"),
                        static_providers=values("static_providers"),
                        conditional_providers=values("conditional_providers"),
                        duplicate_primary=bool(raw.get("duplicate_primary")),
                        needs_attention=bool(raw.get("needs_attention")),
                    )
                )

        return FinchSharedCoveragePreview(
            snapshot_key=snapshot.snapshot_key,
            plan_id=_clean(body.get("plan_id")),
            name=_clean(body.get("name")),
            trial_id=_clean(body.get("trial_id")),
            team_name=_clean(body.get("team_name")),
            difficulty=_clean(body.get("difficulty")),
            total_effects=count("total_effects"),
            covered=count("covered"),
            missing=count("missing"),
            needs_attention=count("needs_attention"),
            duplicate_primary=count("duplicate_primary"),
            unresolved_chairs=count("unresolved_chairs"),
            effects=tuple(rows),
            published_by=snapshot.published_by,
            updated_at=snapshot.updated_at,
        )

    def publish(self, plan: RaidPlan) -> FinchCoveragePublishResult:
        payload = shared_coverage_payload(
            plan,
            build_service=self.build_service,
            database_path=self.database_path,
        )
        snapshot = self.client.publish_shared_coverage(
            snapshot_key=plan.plan_id,
            payload=payload,
            schema_version=_SHARED_COVERAGE_SCHEMA_VERSION,
        )
        return FinchCoveragePublishResult(
            snapshot_key=snapshot.snapshot_key,
            published_by=snapshot.published_by,
            updated_at=snapshot.updated_at,
        )

    def list_shared(self) -> tuple[FinchSharedCoveragePreview, ...]:
        return tuple(
            self.preview(snapshot)
            for snapshot in self.client.shared_coverage_snapshots()
        )

    def get_shared(self, snapshot_key: str) -> FinchSharedCoveragePreview:
        return self.preview(self.client.shared_coverage(snapshot_key))


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
) -> FinchSharedCoverageService:
    return FinchSharedCoverageService(
        client=_configured_client(settings_path=settings_path, timeout=timeout),
        build_service=BuildService(data_dir / "builds.json"),
        database_path=database_path,
    )


def publish_coverage_to_finch(
    *,
    plan_id: str,
    raid_plans_path: Path | None = None,
    data_dir: Path | None = None,
    database_path: Path | None = None,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> FinchCoveragePublishResult:
    root = Path(data_dir or get_data_dir())
    plans = RaidPlanRepository(Path(raid_plans_path or (root / "raid_plans.json")))
    plan = plans.get(plan_id)
    if plan is None:
        raise ValueError(f"Saved Raid Plan {plan_id!r} does not exist.")
    return _service(
        data_dir=root,
        database_path=Path(database_path or DEFAULT_DATABASE),
        settings_path=settings_path,
        timeout=timeout,
    ).publish(plan)


def list_shared_coverage_from_finch(
    *,
    data_dir: Path | None = None,
    database_path: Path | None = None,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> tuple[FinchSharedCoveragePreview, ...]:
    root = Path(data_dir or get_data_dir())
    return _service(
        data_dir=root,
        database_path=Path(database_path or DEFAULT_DATABASE),
        settings_path=settings_path,
        timeout=timeout,
    ).list_shared()


__all__ = [
    "COVERAGE_NAMES",
    "FinchCoveragePublishResult",
    "FinchSharedCoverageEffect",
    "FinchSharedCoveragePreview",
    "FinchSharedCoverageService",
    "list_shared_coverage_from_finch",
    "publish_coverage_to_finch",
    "shared_coverage_payload",
]
