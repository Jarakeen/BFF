from pathlib import Path

import app
from ui import encounter_position_gif_export_support


def test_gif_export_uses_existing_timeline_row_and_scene_renderer() -> None:
    source = Path(encounter_position_gif_export_support.__file__).read_text(encoding="utf-8")

    assert 'QPushButton("Export GIF")' in source
    assert "row.addWidget(button)" in source
    assert "root.insertWidget" not in source
    assert "board.scene.render" in source
    assert "Step names and notes appear in a caption strip" in source


def test_gif_export_exposes_share_friendly_settings_and_save_dialog() -> None:
    source = Path(encounter_position_gif_export_support.__file__).read_text(encoding="utf-8")

    for text in (
        "Frame rate",
        "Size",
        "Pause on each step",
        "Loop continuously",
        "Animated GIF (*.gif)",
        "raid-map-animation.gif",
    ):
        assert text in source


def test_gif_export_is_installed_before_main_window_construction() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "install_encounter_position_gif_export_support" in source
    assert "install_encounter_position_gif_export_support()" in source
    assert source.index("install_encounter_position_gif_export_support()") < source.index(
        "from ui.main_window import MainWindow"
    )


def test_project_requirements_include_pillow_for_animated_gif_encoding() -> None:
    requirements = (Path(app.__file__).parent / "requirements.txt").read_text(encoding="utf-8")

    assert "Pillow>=10.2" in requirements
