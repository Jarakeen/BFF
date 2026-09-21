from __future__ import annotations

from types import SimpleNamespace

from services import finch_collaboration_overview_service as module
from services.finch_collaboration_overview_service import (
    compose_collaboration_rows,
    load_finch_collaboration_overview,
)


def test_overview_composes_all_shared_domains_with_owner_routes() -> None:
    rows = compose_collaboration_rows(
        teams=(
            SimpleNamespace(
                team_name="Performance Mode",
                member_count=12,
                current_focus="Swashbuckler Supreme",
                published_by="Jarakeen",
                updated_at="2026-09-21T02:00:00+00:00",
                provenance="Updated on Finch since copy • local: Performance Mode (Shared Copy)",
            ),
        ),
        raid_plans=(
            SimpleNamespace(
                name="Performance Mode RG",
                trial_id="rockgrove",
                member_count=12,
                team_name="Performance Mode",
                published_by="BFF",
                updated_at="2026-09-21T02:01:00+00:00",
                provenance="Not copied locally",
            ),
        ),
        readiness=(
            SimpleNamespace(
                name="Performance Mode RG",
                plan_id="rg-pm",
                total=12,
                human_ready=9,
                build_gaps=1,
                coverage_gaps=2,
                published_by="BFF",
                updated_at="2026-09-21T02:02:00+00:00",
            ),
        ),
        coverage=(
            SimpleNamespace(
                name="Performance Mode RG",
                plan_id="rg-pm",
                total_effects=16,
                covered=14,
                missing=2,
                needs_attention=2,
                published_by="BFF",
                updated_at="2026-09-21T02:03:00+00:00",
            ),
        ),
    )

    assert [row.kind for row in rows] == [
        "Team",
        "Raid Plan",
        "Readiness",
        "Coverage",
    ]
    assert [row.route for row in rows] == [
        "roster_workspace",
        "raid_plans",
        "readiness",
        "console:7",
    ]
    assert "Updated on Finch since copy" in rows[0].status
    assert rows[2].status == "Read-only snapshot"
    assert rows[3].summary == "14/16 covered • 2 missing • 2 need attention"


def test_overview_loads_partial_results_when_one_domain_fails(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        module,
        "list_shared_teams_from_finch",
        lambda **kwargs: (
            SimpleNamespace(
                team_name="Performance Mode",
                member_count=12,
                current_focus="",
                published_by="Jarakeen",
                updated_at="2026-09-21T02:00:00+00:00",
                provenance="Not copied locally",
            ),
        ),
    )
    monkeypatch.setattr(
        module,
        "list_shared_raid_plans_from_finch",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("plan endpoint unavailable")),
    )
    monkeypatch.setattr(module, "list_shared_readiness_from_finch", lambda **kwargs: ())
    monkeypatch.setattr(module, "list_shared_coverage_from_finch", lambda **kwargs: ())

    overview = load_finch_collaboration_overview(
        data_dir=tmp_path,
        database_path=tmp_path / "eso.db",
        raid_plans_path=tmp_path / "raid_plans.json",
        settings_path=tmp_path / "settings.json",
    )

    assert len(overview.rows) == 1
    assert overview.rows[0].kind == "Team"
    assert len(overview.errors) == 1
    assert overview.errors[0].startswith("Raid Plans: RuntimeError:")


def test_overview_service_has_no_publish_or_import_authority() -> None:
    source = __import__("pathlib").Path(
        "services/finch_collaboration_overview_service.py"
    ).read_text(encoding="utf-8")

    assert "publish_" not in source
    assert "import_shared_team_from_finch" not in source
    assert "import_shared_raid_plan_from_finch" not in source
