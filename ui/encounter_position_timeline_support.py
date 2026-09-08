from __future__ import annotations

"""Position Timeline UI/playback for the Encounters Raid Map.

This is intentionally a thin teaching layer over EncounterBoard.  It captures
named user-authored board states and interpolates token/zone positions between
them.  Nothing here promotes those positions into canonical encounter data.
"""

from dataclasses import replace
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from services.encounter_position_timeline import (
    PositionTimeline,
    PositionTimelineStep,
    PositionTimelineStore,
    TimelineItemState,
    bounded_duration,
    item_key,
)


_INSTALLED = False


def _board_items(board):
    from ui.components.encounter_board import EncounterToken, EncounterZone

    rows = []
    duplicate_counts: dict[tuple[str, str, str], int] = {}

    # Sort only to make duplicate-label ordinals deterministic after restart.
    candidates = []
    for item in board.scene.items():
        if isinstance(item, EncounterToken):
            candidates.append(("token", item.kind, item.label, item))
        elif isinstance(item, EncounterZone):
            candidates.append(("zone", item.zone_type, item.label, item))
    candidates.sort(
        key=lambda row: (
            row[0],
            str(row[1]).casefold(),
            str(row[2]).casefold(),
            round(row[3].pos().x(), 3),
            round(row[3].pos().y(), 3),
        )
    )

    for family, kind, label, item in candidates:
        duplicate = (family, str(kind).casefold(), str(label).casefold())
        duplicate_counts[duplicate] = duplicate_counts.get(duplicate, 0) + 1
        ordinal = duplicate_counts[duplicate]
        stable_id = getattr(item, "_position_timeline_id", "") or item_key(
            family, str(kind), str(label), ordinal
        )
        item._position_timeline_id = stable_id
        rows.append((stable_id, family, str(kind), str(label), item))
    return rows


def _capture_step(board, *, name: str, note: str, duration: float) -> PositionTimelineStep:
    from ui.components.encounter_board import EncounterZone, SCENE_H, SCENE_W

    states = []
    for stable_id, family, kind, label, item in _board_items(board):
        radius = float(item.radius) if isinstance(item, EncounterZone) else float(getattr(item, "radius", 0.0))
        states.append(
            TimelineItemState(
                item_id=stable_id,
                family=family,
                kind=kind,
                label=label,
                x=max(0.0, min(1.0, item.pos().x() / SCENE_W)),
                y=max(0.0, min(1.0, item.pos().y() / SCENE_H)),
                radius=radius,
                visible=item.isVisible(),
            )
        )
    return PositionTimelineStep(
        name=str(name or "Step").strip() or "Step",
        note=str(note or ""),
        duration_seconds=bounded_duration(duration),
        items=tuple(states),
    )


def _item_lookup(board):
    return {stable_id: item for stable_id, _family, _kind, _label, item in _board_items(board)}


def _apply_step(board, step: PositionTimelineStep) -> None:
    from ui.components.encounter_board import EncounterZone, SCENE_H, SCENE_W

    lookup = _item_lookup(board)
    for state in step.items:
        item = lookup.get(state.item_id)
        if item is None:
            continue
        item.setVisible(bool(state.visible))
        item.setPos(state.x * SCENE_W, state.y * SCENE_H)
        if isinstance(item, EncounterZone) and state.radius > 0:
            item.set_radius(state.radius)
    board.scene.update()


def _save_timeline(board) -> None:
    board._position_timeline_store.save(board._position_timeline)


def _refresh_step_picker(board, preferred: int | None = None) -> None:
    combo = board.position_timeline_step_combo
    combo.blockSignals(True)
    combo.clear()
    for index, step in enumerate(board._position_timeline.steps):
        combo.addItem(f"{index + 1}. {step.name}", index)
    combo.blockSignals(False)

    if combo.count() == 0:
        board.position_timeline_note.setText("")
        board.position_timeline_duration.setValue(2.0)
        return
    index = preferred if preferred is not None else 0
    index = max(0, min(combo.count() - 1, int(index)))
    combo.setCurrentIndex(index)
    _select_step(board, index)


def _select_step(board, index: int) -> None:
    if index < 0 or index >= len(board._position_timeline.steps):
        return
    step = board._position_timeline.steps[index]
    board.position_timeline_note.blockSignals(True)
    board.position_timeline_note.setText(step.note)
    board.position_timeline_note.blockSignals(False)
    board.position_timeline_duration.blockSignals(True)
    board.position_timeline_duration.setValue(step.duration_seconds)
    board.position_timeline_duration.blockSignals(False)
    _apply_step(board, step)


def _replace_step(board, index: int, step: PositionTimelineStep) -> None:
    steps = list(board._position_timeline.steps)
    if index < 0 or index >= len(steps):
        return
    steps[index] = step
    board._position_timeline = PositionTimeline(steps=tuple(steps))
    _save_timeline(board)
    _refresh_step_picker(board, index)


def _add_step(board) -> None:
    number = len(board._position_timeline.steps) + 1
    step = _capture_step(
        board,
        name=f"Step {number}",
        note="",
        duration=board.position_timeline_duration.value(),
    )
    board._position_timeline = PositionTimeline(
        steps=board._position_timeline.steps + (step,)
    )
    _save_timeline(board)
    _refresh_step_picker(board, len(board._position_timeline.steps) - 1)


def _duplicate_step(board) -> None:
    index = board.position_timeline_step_combo.currentIndex()
    if index < 0 or index >= len(board._position_timeline.steps):
        return
    source = board._position_timeline.steps[index]
    copy = replace(source, name=f"{source.name} Copy")
    steps = list(board._position_timeline.steps)
    steps.insert(index + 1, copy)
    board._position_timeline = PositionTimeline(steps=tuple(steps))
    _save_timeline(board)
    _refresh_step_picker(board, index + 1)


def _save_current_step(board) -> None:
    index = board.position_timeline_step_combo.currentIndex()
    if index < 0 or index >= len(board._position_timeline.steps):
        return
    current = board._position_timeline.steps[index]
    step = _capture_step(
        board,
        name=current.name,
        note=board.position_timeline_note.text(),
        duration=board.position_timeline_duration.value(),
    )
    _replace_step(board, index, step)


def _delete_step(board) -> None:
    index = board.position_timeline_step_combo.currentIndex()
    if index < 0 or index >= len(board._position_timeline.steps):
        return
    steps = list(board._position_timeline.steps)
    del steps[index]
    board._position_timeline = PositionTimeline(steps=tuple(steps))
    _save_timeline(board)
    _refresh_step_picker(board, min(index, len(steps) - 1))


def _move_step(board, delta: int) -> None:
    index = board.position_timeline_step_combo.currentIndex()
    target = index + delta
    if index < 0 or target < 0 or target >= len(board._position_timeline.steps):
        return
    _stop_playback(board)
    _select_step(board, target)
    board.position_timeline_step_combo.setCurrentIndex(target)


def _start_transition(board, from_index: int, to_index: int) -> None:
    from ui.components.encounter_board import SCENE_H, SCENE_W

    if from_index < 0 or to_index < 0:
        return
    if from_index >= len(board._position_timeline.steps) or to_index >= len(board._position_timeline.steps):
        return

    source = board._position_timeline.steps[from_index]
    target = board._position_timeline.steps[to_index]
    lookup = _item_lookup(board)
    source_by_id = {state.item_id: state for state in source.items}
    target_by_id = {state.item_id: state for state in target.items}

    transitions = []
    for item_id, target_state in target_by_id.items():
        item = lookup.get(item_id)
        if item is None:
            continue
        source_state = source_by_id.get(item_id)
        if source_state is None:
            source_x = item.pos().x() / SCENE_W
            source_y = item.pos().y() / SCENE_H
        else:
            source_x, source_y = source_state.x, source_state.y
        transitions.append((item, source_x, source_y, target_state))

    board._position_timeline_transition = transitions
    board._position_timeline_started_at = time.monotonic()
    board._position_timeline_duration_seconds = bounded_duration(target.duration_seconds)
    board._position_timeline_target_index = to_index
    board._position_timeline_timer.start(16)


def _animation_tick(board) -> None:
    from ui.components.encounter_board import EncounterZone, SCENE_H, SCENE_W

    duration = max(0.001, board._position_timeline_duration_seconds)
    progress = min(1.0, (time.monotonic() - board._position_timeline_started_at) / duration)
    # Smoothstep is still deterministic and avoids abrupt starts/stops without
    # pretending movement follows an encounter-specific path.
    eased = progress * progress * (3.0 - 2.0 * progress)

    for item, source_x, source_y, target in board._position_timeline_transition:
        x = source_x + (target.x - source_x) * eased
        y = source_y + (target.y - source_y) * eased
        item.setVisible(True if progress < 1.0 else bool(target.visible))
        item.setPos(x * SCENE_W, y * SCENE_H)
        if isinstance(item, EncounterZone) and target.radius > 0 and progress >= 1.0:
            item.set_radius(target.radius)
    board.scene.update()

    if progress < 1.0:
        return

    board._position_timeline_timer.stop()
    target_index = board._position_timeline_target_index
    board.position_timeline_step_combo.setCurrentIndex(target_index)
    _select_step(board, target_index)
    if board._position_timeline_playing and target_index + 1 < len(board._position_timeline.steps):
        _start_transition(board, target_index, target_index + 1)
    else:
        board._position_timeline_playing = False
        board.position_timeline_play_button.setText("▶ Play")


def _play(board) -> None:
    if len(board._position_timeline.steps) < 2:
        return
    index = board.position_timeline_step_combo.currentIndex()
    if index < 0:
        index = 0
    if index >= len(board._position_timeline.steps) - 1:
        index = 0
        board.position_timeline_step_combo.setCurrentIndex(0)
        _select_step(board, 0)
    board._position_timeline_playing = True
    board.position_timeline_play_button.setText("▶ Playing")
    _start_transition(board, index, index + 1)


def _stop_playback(board) -> None:
    board._position_timeline_playing = False
    if hasattr(board, "_position_timeline_timer"):
        board._position_timeline_timer.stop()
    if hasattr(board, "position_timeline_play_button"):
        board.position_timeline_play_button.setText("▶ Play")


def _timeline_panel(board) -> QWidget:
    panel = QWidget(board)
    row = QHBoxLayout(panel)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(5)

    title = QLabel("POSITION TIMELINE")
    title.setProperty("sidebarHeading", True)
    row.addWidget(title)

    board.position_timeline_step_combo = QComboBox()
    board.position_timeline_step_combo.setMinimumWidth(150)
    board.position_timeline_step_combo.currentIndexChanged.connect(
        lambda index: _select_step(board, index)
    )
    row.addWidget(board.position_timeline_step_combo)

    add = QPushButton("+ Step")
    add.clicked.connect(lambda: _add_step(board))
    row.addWidget(add)

    duplicate = QPushButton("Duplicate")
    duplicate.clicked.connect(lambda: _duplicate_step(board))
    row.addWidget(duplicate)

    save = QPushButton("Save Step")
    save.clicked.connect(lambda: _save_current_step(board))
    row.addWidget(save)

    delete = QPushButton("Delete")
    delete.clicked.connect(lambda: _delete_step(board))
    row.addWidget(delete)

    previous = QPushButton("◀")
    previous.setToolTip("Previous positioning step")
    previous.clicked.connect(lambda: _move_step(board, -1))
    row.addWidget(previous)

    board.position_timeline_play_button = QPushButton("▶ Play")
    board.position_timeline_play_button.setProperty("primary", True)
    board.position_timeline_play_button.clicked.connect(lambda: _play(board))
    row.addWidget(board.position_timeline_play_button)

    pause = QPushButton("⏸")
    pause.setToolTip("Pause positioning playback")
    pause.clicked.connect(lambda: _stop_playback(board))
    row.addWidget(pause)

    next_button = QPushButton("▶")
    next_button.setToolTip("Next positioning step")
    next_button.clicked.connect(lambda: _move_step(board, 1))
    row.addWidget(next_button)

    duration_label = QLabel("Move")
    row.addWidget(duration_label)
    board.position_timeline_duration = QDoubleSpinBox()
    board.position_timeline_duration.setRange(0.2, 30.0)
    board.position_timeline_duration.setSingleStep(0.5)
    board.position_timeline_duration.setDecimals(1)
    board.position_timeline_duration.setSuffix(" s")
    board.position_timeline_duration.setValue(2.0)
    board.position_timeline_duration.setToolTip("Time used to move into this step")
    row.addWidget(board.position_timeline_duration)

    board.position_timeline_note = QLineEdit()
    board.position_timeline_note.setPlaceholderText("Step note, e.g. Healers split; DDs collapse center")
    board.position_timeline_note.setMinimumWidth(240)
    row.addWidget(board.position_timeline_note, 1)

    return panel


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components.encounter_board import EncounterBoard

    original_init = EncounterBoard.__init__
    original_build_ui = EncounterBoard._build_ui

    def build_ui_with_timeline(self):
        original_build_ui(self)
        root = self.layout()
        if root is not None:
            # Existing layout ends with hint + graphics view. Put the teaching
            # timeline immediately above those so board-edit tools stay grouped.
            insert_at = max(0, root.count() - 2)
            root.insertWidget(insert_at, _timeline_panel(self))

    def init_with_timeline(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._position_timeline_store = PositionTimelineStore(
            self.data_dir / "encounter_positioning_timeline.json"
        )
        self._position_timeline = self._position_timeline_store.load()
        self._position_timeline_timer = QTimer(self)
        self._position_timeline_timer.timeout.connect(lambda: _animation_tick(self))
        self._position_timeline_playing = False
        self._position_timeline_transition = []
        self._position_timeline_started_at = 0.0
        self._position_timeline_duration_seconds = 2.0
        self._position_timeline_target_index = -1
        _refresh_step_picker(self)

    EncounterBoard._build_ui = build_ui_with_timeline
    EncounterBoard.__init__ = init_with_timeline
    _INSTALLED = True
