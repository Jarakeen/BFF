from pathlib import Path


def test_raid_plan_review_routes_to_review_journal():
    source = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")
    assert '("Review", "raid_review")' in source
    assert '("Review", "console:3")' not in source


def test_live_raid_owns_note_editor_and_archives_review_note():
    source = Path("ui/city_live_raid_page.py").read_text(encoding="utf-8")
    assert "self.run_notes_edit = QTextEdit()" in source
    assert "self.user_state.save_review_note(" in source
    assert "self.run_notes_edit.setEnabled(not paused)" in source


def test_review_page_is_registered_and_top_gear_is_named_for_users():
    main = Path("ui/main_window.py").read_text(encoding="utf-8")
    review = Path("ui/raid_review_page.py").read_text(encoding="utf-8")
    top_gear = Path("ui/capabilities_page.py").read_text(encoding="utf-8")
    sidebar = Path("ui/components/foundry_sidebar.py").read_text(encoding="utf-8")

    assert '"raid_review": RaidReviewPage(),' in main
    assert 'title="Review"' in review
    assert 'title="Top Gear"' in top_gear
    assert '("Review", "raid_review")' in sidebar


def test_live_notes_no_longer_use_accessibility_monkey_patch():
    source = Path("ui/urban_wilderness_accessibility_polish.py").read_text(encoding="utf-8")
    assert "city_live_raid_page.CityLiveRaidPage._build_ui =" not in source
    assert "city_live_raid_page.CityLiveRaidPage._render_plan =" not in source
