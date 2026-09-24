from pathlib import Path


def test_successful_assignment_save_does_not_rebuild_live_widgets() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    method = source[
        source.index("    def save_current_plan(self)"):
        source.index("    def _open_assignments", source.index("    def save_current_plan(self)"))
    ]

    assert "self._navigation_baseline_plan = persisted" in method
    assert "self.refresh_personnel()" not in method
    assert "self.apply_plan(persisted)" not in method
    assert "self.refresh_saved_plan_picker(select_plan_id=persisted.plan_id)" in method
    assert "except Exception as exc:" in method


def test_city_assignment_post_save_refresh_is_nonfatal() -> None:
    source = Path("ui/city_raid_assignments_page.py").read_text(encoding="utf-8")
    method = source[
        source.index("    def save_current_plan(self):"):
        source.index("\n\n\n__all__")
    ]

    assert "saved = super().save_current_plan()" in method
    assert "try:" in method
    assert "self._refresh_city_assignment_rows()" in method
    assert "except Exception as exc:" in method
    assert "Assignments saved, but the summary could not refresh" in method
