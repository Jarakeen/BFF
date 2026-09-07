from pathlib import Path


def test_gear_lookup_exposes_trial_comp_bookmark_controls() -> None:
    source = Path("ui/gear_lookup_bookmark_support.py").read_text(encoding="utf-8")

    assert "StickerbookBookmarkService" in source
    assert 'page._context_field("SHORTLIST PROFILE", profile)' in source
    assert 'show.addItem("★ Bookmarked", "bookmarked")' in source
    assert 'QPushButton("☆ Save for Trial Comp")' in source
    assert 'details.set_header_action(button)' in source
    assert 'item.setText(f"★ {text}" if set_id in bookmarked else text)' in source


def test_gear_lookup_bookmarks_share_existing_profile_aware_shortlist() -> None:
    source = Path("ui/gear_lookup_bookmark_support.py").read_text(encoding="utf-8")
    stickerbook = Path("ui/stickerbook_bookmark_support.py").read_text(encoding="utf-8")

    assert "StickerbookBookmarkService" in source
    assert "StickerbookBookmarkService" in stickerbook
    assert "bookmarked_set_ids(_profile(page))" in source
    assert "service.set_bookmarked(profile, int(set_id), not current)" in source


def test_gear_lookup_bookmarks_install_before_main_window_construction() -> None:
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    assert "install_gear_lookup_bookmarks()" in installer
    assert "install_stickerbook_bookmarks()" in installer
