from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_raid_map_base_controls_are_grouped_by_function() -> None:
    source = _source("ui/components/encounter_board.py")
    start = source.index("    def _build_ui(self):")
    build = source[start:source.index("    def _draw_arena", start)]

    actors = build.index('QLabel("ACTORS")')
    mechanics = build.index('QLabel("MECHANICS & AREAS")')
    layout = build.index('QLabel("LAYOUT & OUTPUT")')

    assert actors < mechanics < layout
    assert actors < build.index('("+ Tank", "tank")') < mechanics
    assert actors < build.index('("+ Healer", "healer")') < mechanics
    assert actors < build.index('("+ DD", "dps")') < mechanics
    assert mechanics < build.index('("+ Portal", "portal")') < layout
    assert mechanics < build.index('("+ AOE", "aoe")') < layout
    assert mechanics < build.index('("+ Stack", "stack")') < layout
    assert layout < build.index('QPushButton("Delete Selected")')
    assert layout < build.index('QPushButton("Fit Arena")')
    assert layout < build.index('QPushButton("Save Layout")')
    assert layout < build.index('QPushButton("Capture Positioning")')


def test_formations_have_their_own_row_between_mechanics_and_layout() -> None:
    source = _source("ui/encounter_board_formation_support.py")

    assert 'formation_label = QLabel("FORMATIONS")' in source
    assert 'apply_button = QPushButton("Apply")' in source
    assert "panel = QWidget(self)" in source
    assert "row = QHBoxLayout(panel)" in source
    assert "root.insertWidget(2, panel)" in source
    assert "insertWidget(insert_at" not in source


def test_edit_reference_and_timeline_keep_distinct_functional_sections() -> None:
    labels = _source("ui/encounter_board_custom_labels_support.py")
    timeline = _source("ui/encounter_position_timeline_support.py")

    assert 'QLabel("EDIT & REFERENCE")' in labels
    assert 'QLabel("REFERENCE POINTS")' in labels
    assert 'QPushButton("Rename")' in labels
    assert 'QLabel("POSITION TIMELINE")' in timeline


def test_map_help_text_is_short_and_task_oriented() -> None:
    source = _source("ui/components/encounter_board.py")

    assert "Drag items to position them." in source
    assert "Timeline and reference tools below preserve their own saved state." in source
    assert "Up to six mini-boss markers may be placed." not in source
