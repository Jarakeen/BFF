from pathlib import Path

from services.team_schedule_share_export import _public_assignment_build


def test_recruit_pdf_build_label_hides_esologs_player_identity() -> None:
    item = {
        "player": "Recruitment Needed",
        "class": "Dragonknight",
        "role": "Off Tank",
        "build": "Dragonknight Tank • Oaxiltso • TotallyNotOurRecruit",
    }

    assert _public_assignment_build(item) == "Dragonknight Tank • Oaxiltso"
    assert "TotallyNotOurRecruit" not in _public_assignment_build(item)


def test_saved_player_pdf_build_label_is_not_modified() -> None:
    item = {
        "player": "Magrat",
        "build": "GH Healer • Personal Variant",
    }

    assert _public_assignment_build(item) == "GH Healer • Personal Variant"


def test_roster_pdf_assignment_section_keeps_only_requested_columns() -> None:
    source = Path("services/team_schedule_share_export.py").read_text(encoding="utf-8")

    assert 'rows = [["PLAYER", "CLASS", "ROLE", "BUILD"]]' in source
    assignment_block = source.split('rows = [["PLAYER", "CLASS", "ROLE", "BUILD"]]', 1)[1]
    assignment_block = assignment_block.split('story.append(Paragraph("PERSONNEL"', 1)[0]
    assert 'item.get("primary")' not in assignment_block
    assert 'item.get("secondary")' not in assignment_block
    assert 'item.get("ready")' not in assignment_block


def test_generated_assignment_player_or_build_click_opens_build_details() -> None:
    source = Path("ui/roster_assignment_build_details_support.py").read_text(
        encoding="utf-8"
    )

    assert "item.column() not in {0, 3}" in source
    assert "_show_assignment_details(page, item.row())" in source
    assert '"GEAR"' in source
    assert '"SKILLS / ABILITIES"' in source
    assert "FrontBarSkills" in source
    assert "BackBarSkills" in source
    assert "Observed/known skills:" in source


def test_assignment_details_are_installed_after_generated_roster_support() -> None:
    source = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    roster_view = source.index("install_comp_builder_roster_view()")
    details = source.index("install_roster_assignment_build_details()")
    assert roster_view < details
