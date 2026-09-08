from __future__ import annotations

"""Animated GIF export for the Raid Map Position Timeline.

The exporter reuses the real QGraphicsScene renderer so exports contain the same
arena, labels, reference anchors, zones, and marker styling shown in the app.
It adds one compact button to the existing Position Timeline row rather than
creating another toolbar row.
"""

from io import BytesIO
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
)

from services.encounter_position_gif_export_service import (
    DEFAULT_FPS,
    DEFAULT_HOLD_SECONDS,
    GifFrameSpec,
    bounded_fps,
    build_frame_plan,
)


_INSTALLED = False


class GifExportSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Raid Map Animation")
        self.setModal(True)

        root = QVBoxLayout(self)
        note = QLabel(
            "Export the Position Timeline as a Discord-friendly animated GIF. "
            "Step names and notes appear in a caption strip below the arena."
        )
        note.setWordWrap(True)
        note.setProperty("pageSubtitle", True)
        root.addWidget(note)

        form = QFormLayout()
        self.fps = QComboBox()
        for value in (8, 10, 12, 15):
            self.fps.addItem(f"{value} fps", value)
        self.fps.setCurrentIndex(self.fps.findData(DEFAULT_FPS))
        form.addRow("Frame rate", self.fps)

        self.scale = QComboBox()
        for label, value in (("50%", 0.5), ("75%", 0.75), ("100%", 1.0)):
            self.scale.addItem(label, value)
        self.scale.setCurrentIndex(self.scale.findData(0.75))
        form.addRow("Size", self.scale)

        self.hold = QDoubleSpinBox()
        self.hold.setRange(0.0, 3.0)
        self.hold.setSingleStep(0.1)
        self.hold.setDecimals(1)
        self.hold.setSuffix(" s")
        self.hold.setValue(DEFAULT_HOLD_SECONDS)
        self.hold.setToolTip("How long to pause on each completed positioning step")
        form.addRow("Pause on each step", self.hold)

        self.loop = QCheckBox("Loop continuously")
        self.loop.setChecked(True)
        form.addRow("Playback", self.loop)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Choose File…")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @property
    def export_fps(self) -> int:
        return bounded_fps(self.fps.currentData())

    @property
    def export_scale(self) -> float:
        return float(self.scale.currentData() or 0.75)

    @property
    def hold_seconds(self) -> float:
        return float(self.hold.value())

    @property
    def should_loop(self) -> bool:
        return bool(self.loop.isChecked())


def _snapshot_scene_state(board):
    from ui.components.encounter_board import EncounterToken, EncounterZone

    rows = []
    for item in board.scene.items():
        if isinstance(item, EncounterToken):
            rows.append((item, item.pos(), item.isVisible(), None))
        elif isinstance(item, EncounterZone):
            rows.append((item, item.pos(), item.isVisible(), float(item.radius)))
    return rows


def _restore_scene_state(board, snapshot) -> None:
    from ui.components.encounter_board import EncounterZone

    for item, position, visible, radius in snapshot:
        item.setVisible(bool(visible))
        item.setPos(position)
        if isinstance(item, EncounterZone) and radius is not None:
            item.set_radius(radius)
    board.scene.update()


def _apply_export_frame(board, spec: GifFrameSpec) -> None:
    from ui import encounter_position_timeline_support as timeline_ui
    from ui.components.encounter_board import EncounterZone, SCENE_H, SCENE_W

    timeline = board._position_timeline
    if spec.from_index == spec.to_index:
        timeline_ui._apply_step(board, timeline.steps[spec.to_index])
        return

    source = timeline.steps[spec.from_index]
    target = timeline.steps[spec.to_index]
    source_by_id = {state.item_id: state for state in source.items}
    target_by_id = {state.item_id: state for state in target.items}
    lookup = timeline_ui._item_lookup(board)
    progress = max(0.0, min(1.0, float(spec.progress)))

    for item_id, target_state in target_by_id.items():
        item = lookup.get(item_id)
        if item is None:
            continue
        source_state = source_by_id.get(item_id) or target_state
        x = source_state.x + (target_state.x - source_state.x) * progress
        y = source_state.y + (target_state.y - source_state.y) * progress
        if source_state.visible and not target_state.visible:
            visible = progress < 1.0
        elif not source_state.visible and target_state.visible:
            visible = progress > 0.0
        else:
            visible = bool(source_state.visible or target_state.visible)
        item.setVisible(visible)
        item.setPos(x * SCENE_W, y * SCENE_H)
        if isinstance(item, EncounterZone):
            start_radius = source_state.radius or target_state.radius
            end_radius = target_state.radius or start_radius
            if start_radius > 0:
                item.set_radius(start_radius + (end_radius - start_radius) * progress)
    board.scene.update()


def _render_qimage(board, spec: GifFrameSpec, scale: float) -> QImage:
    from ui.components.encounter_board import SCENE_H, SCENE_W

    _apply_export_frame(board, spec)
    scale = max(0.35, min(1.5, float(scale)))
    width = max(320, int(round(SCENE_W * scale)))
    arena_height = max(180, int(round(SCENE_H * scale)))
    caption_height = max(48, int(round(66 * scale)))

    image = QImage(
        width,
        arena_height + caption_height,
        QImage.Format.Format_ARGB32,
    )
    image.fill(QColor("#101214"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    board.scene.render(
        painter,
        QRectF(0.0, 0.0, float(width), float(arena_height)),
        QRectF(0.0, 0.0, SCENE_W, SCENE_H),
        Qt.AspectRatioMode.IgnoreAspectRatio,
    )

    painter.fillRect(
        QRectF(0.0, float(arena_height), float(width), float(caption_height)),
        QColor("#17191B"),
    )
    step = board._position_timeline.steps[spec.caption_index]
    title_font = QFont("Segoe UI", max(9, int(round(11 * scale))), QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.setPen(QColor("#EFEDE7"))
    painter.drawText(
        QRectF(14.0, arena_height + 6.0, width - 28.0, 22.0),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        step.name,
    )

    note_font = QFont("Segoe UI", max(8, int(round(9 * scale))))
    painter.setFont(note_font)
    painter.setPen(QColor("#B8BABD"))
    note = str(step.note or "").strip() or "Positioning step"
    painter.drawText(
        QRectF(14.0, arena_height + 27.0, width - 28.0, caption_height - 31.0),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        note,
    )
    painter.end()
    return image


def _qimage_to_pillow(image: QImage):
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - dependency guard for old installs
        raise RuntimeError(
            "Animated GIF export requires Pillow. Install the current project requirements."
        ) from exc

    payload = QByteArray()
    buffer = QBuffer(payload)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise RuntimeError("Could not open the in-memory GIF frame buffer.")
    try:
        if not image.save(buffer, "PNG"):
            raise RuntimeError("Could not encode a Raid Map frame.")
    finally:
        buffer.close()

    frame = Image.open(BytesIO(bytes(payload))).convert("RGBA")
    return frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)


def export_position_timeline_gif(
    board,
    destination: Path,
    *,
    fps: int,
    scale: float,
    hold_seconds: float,
    loop: bool,
) -> int:
    """Render and write the current timeline. Returns the number of frames."""

    try:
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Animated GIF export requires Pillow. Install the current project requirements."
        ) from exc

    plan = build_frame_plan(
        board._position_timeline,
        fps=fps,
        hold_seconds=hold_seconds,
    )
    if len(board._position_timeline.steps) < 2 or not plan:
        raise ValueError("Add at least two Position Timeline steps before exporting.")

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    snapshot = _snapshot_scene_state(board)
    selected_index = board.position_timeline_step_combo.currentIndex()
    progress = QProgressDialog(
        "Rendering Raid Map animation…",
        "Cancel",
        0,
        len(plan),
        board,
    )
    progress.setWindowTitle("Export Animated Raid Map")
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)

    frames = []
    board.view.setUpdatesEnabled(False)
    try:
        for index, spec in enumerate(plan):
            if progress.wasCanceled():
                raise InterruptedError("GIF export canceled.")
            frames.append(_qimage_to_pillow(_render_qimage(board, spec, scale)))
            progress.setValue(index + 1)
            if index % 4 == 0:
                QApplication.processEvents()
    finally:
        _restore_scene_state(board, snapshot)
        board.view.setUpdatesEnabled(True)
        board.view.viewport().update()
        if selected_index >= 0:
            board.position_timeline_step_combo.blockSignals(True)
            board.position_timeline_step_combo.setCurrentIndex(selected_index)
            board.position_timeline_step_combo.blockSignals(False)
        progress.close()

    if not frames:
        raise RuntimeError("No Raid Map frames were rendered.")

    frame_duration_ms = max(20, int(round(1000 / bounded_fps(fps))))
    save_args = {
        "save_all": True,
        "append_images": frames[1:],
        "duration": frame_duration_ms,
        "disposal": 2,
        "optimize": False,
    }
    if loop:
        save_args["loop"] = 0
    frames[0].save(str(destination), format="GIF", **save_args)
    return len(frames)


def _export_from_board(board) -> None:
    if len(getattr(board, "_position_timeline", ()).steps) < 2:
        QMessageBox.information(
            board,
            "Position Timeline",
            "Add at least two Position Timeline steps before exporting an animation.",
        )
        return

    settings = GifExportSettingsDialog(board)
    if settings.exec() != QDialog.DialogCode.Accepted:
        return

    default_path = Path.home() / "raid-map-animation.gif"
    filename, _selected_filter = QFileDialog.getSaveFileName(
        board,
        "Export Animated Raid Map",
        str(default_path),
        "Animated GIF (*.gif)",
    )
    if not filename:
        return
    destination = Path(filename)
    if destination.suffix.casefold() != ".gif":
        destination = destination.with_suffix(".gif")

    try:
        frame_count = export_position_timeline_gif(
            board,
            destination,
            fps=settings.export_fps,
            scale=settings.export_scale,
            hold_seconds=settings.hold_seconds,
            loop=settings.should_loop,
        )
    except InterruptedError:
        return
    except (OSError, RuntimeError, ValueError) as exc:
        QMessageBox.critical(board, "GIF Export Failed", str(exc))
        return

    QMessageBox.information(
        board,
        "Raid Map Exported",
        f"Animated Raid Map saved to:\n{destination}\n\n{frame_count} frames rendered.",
    )


def _add_export_button(board) -> None:
    combo = getattr(board, "position_timeline_step_combo", None)
    if combo is None:
        return
    panel = combo.parentWidget()
    row = panel.layout() if panel is not None else None
    if row is None or hasattr(board, "position_timeline_export_gif_button"):
        return

    button = QPushButton("Export GIF")
    button.setToolTip("Export the Position Timeline as an animated GIF")
    button.clicked.connect(lambda: _export_from_board(board))
    board.position_timeline_export_gif_button = button
    row.addWidget(button)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components.encounter_board import EncounterBoard

    original_init = EncounterBoard.__init__

    def init_with_gif_export(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _add_export_button(self)

    EncounterBoard.__init__ = init_with_gif_export
    _INSTALLED = True
