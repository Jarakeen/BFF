from pathlib import Path


def test_finch_shared_plan_runtime_uses_canonical_user_database() -> None:
    service = Path("services/finch_shared_import_service.py").read_text(encoding="utf-8")
    page = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert "get_user_database_path" in service
    assert 'get_data_dir() / "raid_plans.json"' not in service
    assert "raid_plans_path=get_user_database_path()" in page
    assert "database_path=get_user_database_path()" in page


def test_shared_plan_import_preserves_published_planned_skills() -> None:
    source = Path("services/finch_shared_import_service.py").read_text(encoding="utf-8")

    assert 'build_summary.get("front_skills")' in source
    assert "planned_skills=tuple(" in source


def test_raid_plan_and_comp_saves_create_database_checkpoints() -> None:
    raid_plan = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")
    comp = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert 'f"save-raid-plan-{visible_before_sync.plan_id}"' in raid_plan
    assert 'f"save-comp-plan-{state.raid_plan_id or state.raid_plan_name or \'new\'}"' in comp
    assert "saved Comp Raid Plan did not round-trip exactly" in comp


def test_comp_handoff_refuses_dirty_or_unverified_plan() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    bind = source[
        source.index("def _bind_plan_comp_builder"):
        source.index("def _open_plan_comp_builder")
    ]
    opener = source[
        source.index("def _open_plan_comp_builder"):
        source.index("def _route_plan_page")
    ]

    assert "has_pending()" in bind
    assert "verified_plan = repository.get(plan.plan_id)" in bind
    assert "verified_plan != plan" in bind
    assert "if not _bind_plan_comp_builder(window, source_page):" in opener


def test_raid_plan_save_does_not_implicitly_promote_personnel() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")
    method = source[
        source.index("    def save_current_plan(self)"):
        source.index("    def _open_assignments", source.index("    def save_current_plan(self)"))
    ]

    assert "_ensure_named_players_in_personnel()" not in method
    assert "self.refresh_personnel()" not in method
    assert "self.apply_plan(persisted)" not in method
    assert "plan = self.current_plan()" in method
    assert "self.plan_repository.save(plan)" in method
