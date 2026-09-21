from __future__ import annotations

from types import SimpleNamespace

from models.raid_plan import RaidPlan, RaidPlanMember
from services.finch_api_client import FinchSharedSnapshot
from services.finch_shared_coverage_service import (
    FinchSharedCoverageService,
    shared_coverage_payload,
)
from services.saved_build_capability_service import RaidCoverageSnapshot


class FakeClient:
    def __init__(self):
        self.published = []
        self.snapshot = FinchSharedSnapshot(
            kind="coverage",
            snapshot_key="rg-pm",
            schema_version=1,
            payload={
                "plan_id": "rg-pm",
                "name": "Performance Mode RG",
                "trial_id": "rockgrove",
                "team_name": "Performance Mode",
                "difficulty": "Veteran",
                "summary": {
                    "total_effects": 2,
                    "covered": 1,
                    "missing": 1,
                    "needs_attention": 1,
                    "duplicate_primary": 0,
                    "unresolved_chairs": 1,
                },
                "effects": [
                    {
                        "effect_name": "Major Courage",
                        "required": True,
                        "coverage_state": "covered",
                        "evidence_state": "assigned_supported",
                        "label": "Covered • Supported",
                        "primary": ["Rylo"],
                        "backup": [],
                        "static_providers": ["Rylo"],
                        "conditional_providers": [],
                        "duplicate_primary": False,
                        "needs_attention": False,
                    }
                ],
            },
            published_by="BFF",
            updated_at="2026-09-21T00:00:00+00:00",
        )

    def publish_shared_coverage(self, *, snapshot_key, payload, schema_version=1):
        self.published.append((snapshot_key, payload, schema_version))
        return FinchSharedSnapshot(
            kind="coverage",
            snapshot_key=snapshot_key,
            schema_version=schema_version,
            payload=payload,
            published_by="Jarakeen",
            updated_at="2026-09-21T00:00:00+00:00",
        )

    def shared_coverage_snapshots(self):
        return (self.snapshot,)

    def shared_coverage(self, snapshot_key):
        assert snapshot_key == "rg-pm"
        return self.snapshot


class FakeScope:
    members = ()
    planned_gear = ()
    unresolved = ("dd-2 unresolved",)

    def primary_for(self, effect_name):
        return ("Rylo",) if effect_name == "Major Courage" else ()

    def secondary_for(self, effect_name):
        return ()


def _plan() -> RaidPlan:
    return RaidPlan(
        plan_id="rg-pm",
        trial_id="rockgrove",
        name="Performance Mode RG",
        team_name="Performance Mode",
        difficulty="Veteran",
        plan_note="private raid lead note",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Rylo",
                roster_member_id=42,
                player_id="private-player-id",
                character_id="private-character-id",
                character_name="Rylo",
                role="Damage Dealer",
                selected_build_id="private-build-id",
                selected_build_name="Support",
                primary_assignment="Major Courage",
                assignment_source="https://private.example/source",
                notes="private chair note",
            ),
        ),
    )


def test_shared_coverage_payload_is_operational_evidence_only(monkeypatch) -> None:
    from services import finch_shared_coverage_service as module

    status = {name: "unverified" for name in module.COVERAGE_NAMES}
    providers = {name: [] for name in module.COVERAGE_NAMES}
    conditional = {name: [] for name in module.COVERAGE_NAMES}
    status["Major Courage"] = "available"
    providers["Major Courage"] = ["Rylo"]
    snapshot = RaidCoverageSnapshot(status, providers, conditional)

    monkeypatch.setattr(
        module,
        "_coverage_snapshot",
        lambda plan, *, build_service, database_path: (FakeScope(), snapshot),
    )

    payload = shared_coverage_payload(
        _plan(),
        build_service=SimpleNamespace(),
        database_path=SimpleNamespace(),
    )

    courage = next(
        row for row in payload["effects"]
        if row["effect_name"] == "Major Courage"
    )
    assert courage["coverage_state"] == "covered"
    assert courage["primary"] == ["Rylo"]
    assert courage["static_providers"] == ["Rylo"]

    rendered = repr(payload)
    for forbidden in (
        "private raid lead note",
        "private chair note",
        "private-player-id",
        "private-character-id",
        "private-build-id",
        "https://private.example/source",
    ):
        assert forbidden not in rendered


def test_shared_coverage_preview_preserves_provider_lists_read_only() -> None:
    client = FakeClient()
    service = FinchSharedCoverageService(
        client=client,
        build_service=SimpleNamespace(),
        database_path=SimpleNamespace(),
    )

    previews = service.list_shared()
    preview = service.get_shared("rg-pm")

    assert previews == (preview,)
    assert preview.covered == 1
    assert preview.missing == 1
    assert preview.unresolved_chairs == 1
    assert preview.effects[0].effect_name == "Major Courage"
    assert preview.effects[0].primary == ("Rylo",)
    assert preview.effects[0].static_providers == ("Rylo",)


def test_coverage_preview_rejects_future_schema_version() -> None:
    snapshot = FinchSharedSnapshot(
        kind="coverage",
        snapshot_key="future",
        schema_version=2,
        payload={"plan_id": "future", "summary": {}, "effects": []},
        published_by="BFF",
        updated_at="2026-09-21T00:00:00+00:00",
    )

    try:
        FinchSharedCoverageService.preview(snapshot)
    except ValueError as exc:
        assert "schema version" in str(exc)
    else:
        raise AssertionError("future Coverage schema should fail closed")
