from pathlib import Path


def test_all_recruit_templates_use_template_inspector_when_available() -> None:
    source = Path("ui/roster_assignment_build_details_support.py").read_text(
        encoding="utf-8"
    )

    assert "find_team_template_inspection" in source
    assert "_template_inspection_for_slot" in source
    assert "inspection.gear_sets" in source
    assert "inspection.skills" in source
    assert "inspection.mundus" in source


def test_assignment_detail_layout_is_consistent_across_sources() -> None:
    source = Path("ui/roster_assignment_build_details_support.py").read_text(
        encoding="utf-8"
    )

    for label in (
        '"GEAR"',
        '"SKILLS / ABILITIES"',
        '"MUNDUS"',
        '"SOURCE"',
        '"UNRESOLVED"',
    ):
        assert label in source


def test_saved_and_template_sources_share_the_same_details_renderer() -> None:
    source = Path("ui/roster_assignment_build_details_support.py").read_text(
        encoding="utf-8"
    )

    assert "if saved_build is not None:" in source
    assert "elif inspection is not None:" in source
    assert 'text.setPlainText(_details_text(page, slot))' in source


def test_observed_player_identity_is_not_rendered_from_template_inspection() -> None:
    source = Path("ui/roster_assignment_build_details_support.py").read_text(
        encoding="utf-8"
    )

    details_block = source.split("def _details_text", 1)[1].split(
        "def _show_assignment_details", 1
    )[0]
    assert "observed_player_name" not in details_block
    assert "_public_build_name" in details_block
