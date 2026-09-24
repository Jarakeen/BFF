from pathlib import Path


def test_coverage_never_renders_empty_without_saved_plan() -> None:
    source = Path("ui/coverage_raid_plan_scope_support.py").read_text(encoding="utf-8")

    assert "def _render_reference_catalog(page) -> None:" in source
    assert 'page.scope_card.set_title("Coverage Reference Catalog")' in source
    assert 'for effect in _effect_names(page):' in source
    assert '"No provider assigned"' in source
    assert "_render_reference_catalog(self)" in source


def test_friend_build_creates_populated_reference_seed_by_default() -> None:
    source = Path("packaging/build_friend.ps1").read_text(encoding="utf-8")

    assert "build_release_user_database_seed.py" in source
    assert "Prepared user database seed: POPULATED REFERENCE RAID" in source
