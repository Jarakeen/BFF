from __future__ import annotations

from models.raid_plan import RaidPlan, RaidPlanMember
from services.finch_api_client import FinchSharedSnapshot
from services.finch_shared_readiness_service import (
    FinchSharedReadinessService,
    shared_readiness_payload,
)
from services.raid_readiness_evidence_service import (
    RaidReadinessEvidence,
    RaidReadinessSeatEvidence,
)


class FakeEvidenceService:
    def evaluate(self, plan):
        assert plan.plan_id == "rg-pm"
        return RaidReadinessEvidence(
            seats=(
                RaidReadinessSeatEvidence(
                    seat_id="healer-1",
                    build_state="ready",
                    build_label="✓ READY",
                    build_detail="Local build detail must stay local",
                    coverage_state="covered",
                    coverage_label="✓ COVERED",
                    coverage_detail="Local coverage detail must stay local",
                ),
                RaidReadinessSeatEvidence(
                    seat_id="dd-1",
                    build_state="planned",
                    build_label="◐ PLANNED",
                    build_detail="Private planned detail",
                    coverage_state="gap",
                    coverage_label="! GAP",
                    coverage_detail="Missing: Major Courage",
                ),
            )
        )


class FakeUserState:
    def __init__(self):
        self.values = {
            ("rg-pm", "healer-1"): True,
            ("rg-pm", "dd-1"): None,
        }

    def human_ready(self, plan_id, seat_id):
        return self.values.get((plan_id, seat_id))


class FakeClient:
    def __init__(self):
        self.published = []
        self.snapshot = FinchSharedSnapshot(
            kind="readiness",
            snapshot_key="rg-pm",
            schema_version=1,
            payload={
                "plan_id": "rg-pm",
                "name": "Performance Mode RG",
                "trial_id": "rockgrove",
                "team_name": "Performance Mode",
                "difficulty": "Veteran",
                "summary": {
                    "total": 2,
                    "build_ready": 1,
                    "build_planned": 1,
                    "build_gaps": 0,
                    "assignment_ready": 1,
                    "coverage_covered": 1,
                    "coverage_gaps": 1,
                    "human_ready": 1,
                    "human_pending": 1,
                },
                "seats": [],
            },
            published_by="BFF",
            updated_at="2026-09-21T00:00:00+00:00",
        )

    def publish_shared_readiness(self, *, snapshot_key, payload, schema_version=1):
        self.published.append((snapshot_key, payload, schema_version))
        return FinchSharedSnapshot(
            kind="readiness",
            snapshot_key=snapshot_key,
            schema_version=schema_version,
            payload=payload,
            published_by="Jarakeen",
            updated_at="2026-09-21T00:00:00+00:00",
        )

    def shared_readiness_snapshots(self):
        return (self.snapshot,)

    def shared_readiness(self, snapshot_key):
        assert snapshot_key == "rg-pm"
        return self.snapshot


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
                seat_id="healer-1",
                gamertag="Magrat",
                roster_member_id=42,
                player_id="private-player-id",
                character_id="private-character-id",
                character_name="Magrat",
                role="Healer",
                selected_build_id="private-build-id",
                selected_build_name="RoJo",
                primary_assignment="Major Slayer",
                notes="private chair note",
            ),
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Rylo",
                character_name="Rylo",
                role="Damage Dealer",
                planned_gear_sets=("Corpsebuster", "Null Arca"),
            ),
        ),
    )


def test_shared_readiness_payload_is_small_operational_state_only() -> None:
    payload = shared_readiness_payload(
        _plan(),
        evidence_service=FakeEvidenceService(),
        user_state=FakeUserState(),
    )

    assert payload["summary"] == {
        "total": 2,
        "build_ready": 1,
        "build_planned": 1,
        "build_gaps": 0,
        "assignment_ready": 1,
        "coverage_covered": 1,
        "coverage_gaps": 1,
        "human_ready": 1,
        "human_pending": 1,
    }
    assert payload["seats"][0] == {
        "seat_id": "healer-1",
        "gamertag": "Magrat",
        "character_name": "Magrat",
        "role": "Healer",
        "build_state": "ready",
        "build_label": "✓ READY",
        "assignment_ready": True,
        "coverage_state": "covered",
        "coverage_label": "✓ COVERED",
        "human_ready": True,
    }

    rendered = repr(payload)
    for forbidden in (
        "private raid lead note",
        "private chair note",
        "private-player-id",
        "private-character-id",
        "private-build-id",
        "Local build detail must stay local",
        "Local coverage detail must stay local",
        "Private planned detail",
    ):
        assert forbidden not in rendered


def test_publish_uses_plan_id_and_readiness_schema_v1() -> None:
    client = FakeClient()
    service = FinchSharedReadinessService(
        client=client,
        evidence_service=FakeEvidenceService(),
        user_state=FakeUserState(),
    )

    result = service.publish(_plan())

    assert client.published[0][0] == "rg-pm"
    assert client.published[0][2] == 1
    assert result.snapshot_key == "rg-pm"
    assert result.published_by == "Jarakeen"


def test_shared_readiness_preview_is_read_only_summary() -> None:
    client = FakeClient()
    user_state = FakeUserState()
    service = FinchSharedReadinessService(
        client=client,
        evidence_service=FakeEvidenceService(),
        user_state=user_state,
    )

    previews = service.list_shared()
    preview = service.get_shared("rg-pm")

    assert previews == (preview,)
    assert preview.plan_id == "rg-pm"
    assert preview.total == 2
    assert preview.build_ready == 1
    assert preview.build_planned == 1
    assert preview.coverage_gaps == 1
    assert preview.human_ready == 1
    assert preview.human_pending == 1
    assert user_state.values[("rg-pm", "dd-1")] is None


def test_readiness_preview_rejects_future_schema_version() -> None:
    snapshot = FinchSharedSnapshot(
        kind="readiness",
        snapshot_key="future",
        schema_version=2,
        payload={"plan_id": "future", "summary": {}},
        published_by="BFF",
        updated_at="2026-09-21T00:00:00+00:00",
    )

    try:
        FinchSharedReadinessService.preview(snapshot)
    except ValueError as exc:
        assert "schema version" in str(exc)
    else:
        raise AssertionError("future readiness schema should fail closed")
