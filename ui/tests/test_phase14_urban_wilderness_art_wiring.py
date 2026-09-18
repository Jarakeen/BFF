from pathlib import Path


def test_readiness_uses_urban_wilderness_note_art_without_layout_growth() -> None:
    source = Path("ui/city_raid_readiness_page.py").read_text(encoding="utf-8")

    assert '"urban_wilderness", "notes", self.filename' in source
    assert '"note1.png"' in source
    assert '"note4.png"' in source
    assert "self.setFixedHeight(150)" in source
    assert "self.setMinimumWidth(0)" in source
    assert "QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed" in source
    assert "KeepAspectRatioByExpanding" in source


def test_raid_map_keeps_original_arena_and_only_overrides_accessible_markers() -> None:
    polish = Path("ui/urban_wilderness_accessibility_polish.py").read_text(encoding="utf-8")
    board = Path("ui/components/encounter_board.py").read_text(encoding="utf-8")

    assert "board.EncounterBoard._draw_arena =" not in polish
    assert 'shell = QColor("#081416")' in board
    assert 'brass = QColor("#6F5A37")' in board
    assert 'stone_light = QColor("#163033")' in board


def test_trial_banner_resolver_knows_requested_trials() -> None:
    source = Path("ui/raid_trial_banner_support.py").read_text(encoding="utf-8")
    page = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")

    assert '("rockgrove", "rockgrove.webp")' in source
    assert '("cloudrest", "cloudrest.webp")' in source
    assert '("ossein cage", "ossein_cage.webp")' in source
    assert '"oc": "ossein_cage.webp"' in source
    assert "trial_banner_path(selected_trial, plan.trial_id, plan.name)" in page
