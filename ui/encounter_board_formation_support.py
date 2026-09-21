from __future__ import annotations

"""Preset raid-stack formations for the Encounters Raid Map.

The formation picker is intentionally a presentation/positioning helper only. It
reuses the board's existing draggable DD/healer markers and is exposed only in
the Urban Wilderness visual theme, inheriting that theme's marker styling and
color-vision behavior.
"""

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton

from services.accessibility_preferences import VISUAL_THEME_URBAN_WILDERNESS

_INSTALLED = False


@dataclass(frozen=True)
class FormationPreset:
    key: str
    label: str
    dps_positions: tuple[tuple[float, float], ...]
    healer_positions: tuple[tuple[float, float], ...]


FORMATION_PRESETS = (
    FormationPreset(
        key="house_stacks",
        label="House Stacks",
        # Canonical house-stack numbering:
        #   5   6   7   8
        #   1   2   3   4
        dps_positions=(
            (360.0, 315.0),
            (440.0, 315.0),
            (520.0, 315.0),
            (600.0, 315.0),
            (360.0, 255.0),
            (440.0, 255.0),
            (520.0, 255.0),
            (600.0, 255.0),
        ),
        healer_positions=((392.5, 355.0), (567.5, 355.0)),
    ),
    FormationPreset(
        key="rainbow_stacks",
        label="Rainbow Stacks",
        # Reference layout:
        #        H1      H2
        #      DD2    DD3
        #   DD1          DD4
        #      DD6    DD7
        # DD5              DD8
        dps_positions=(
            (375.0, 285.0),
            (445.0, 250.0),
            (515.0, 250.0),
            (585.0, 285.0),
            (315.0, 340.0),
            (415.0, 320.0),
            (545.0, 320.0),
            (645.0, 340.0),
        ),
        healer_positions=((365.0, 195.0), (595.0, 195.0)),
    ),
)

_PRESET_BY_KEY = {preset.key: preset for preset in FORMATION_PRESETS}


def _first_spacer_index(layout) -> int:
    for index in range(layout.count()):
        if layout.itemAt(index).spacerItem() is not None:
            return index
    return layout.count()


def _role_items(board, kind: str):
    return sorted(
        (item for item in board._token_items() if item.kind == kind),
        key=lambda item: (str(item.label).casefold(), item.pos().x(), item.pos().y()),
    )


def _ensure_role_items(board, kind: str, count: int):
    items = _role_items(board, kind)
    while len(items) < count:
        number = len(items) + 1
        label = f"DD {number}" if kind == "dps" else f"Healer {number}"
        token = board._add_token(kind, label, 480.0, 360.0)
        board._counts[kind] = max(board._counts.get(kind, 0), number)
        items.append(token)
    return items


def apply_formation(board, preset_key: str) -> bool:
    """Arrange the first eight DDs and first two healers without deleting extras."""
    preset = _PRESET_BY_KEY.get(str(preset_key or "").strip())
    if preset is None:
        return False

    dps_items = _ensure_role_items(board, "dps", len(preset.dps_positions))
    healer_items = _ensure_role_items(board, "healer", len(preset.healer_positions))

    for index, ((x, y), token) in enumerate(
        zip(preset.dps_positions, dps_items, strict=True),
        start=1,
    ):
        token.label = f"DD {index}"
        token.setPos(x, y)
        token.update()

    for index, ((x, y), token) in enumerate(
        zip(preset.healer_positions, healer_items, strict=True),
        start=1,
    ):
        token.label = f"Healer {index}"
        token.setPos(x, y)
        token.update()

    board.scene.update()
    board.view.viewport().update()
    return True


def install() -> None:
    """Add formation presets to the existing second Raid Map toolbar row."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.components import encounter_board as encounter_board

    original_init = encounter_board.EncounterBoard.__init__

    def init_with_formations(self, parent=None):
        original_init(self, parent)

        app = QApplication.instance()
        if app is None or app.property("visualTheme") != VISUAL_THEME_URBAN_WILDERNESS:
            return

        root = self.layout()
        zone_toolbar = None
        if root is not None and root.count() > 1:
            zone_toolbar = root.itemAt(1).layout()
        if zone_toolbar is None:
            return

        self.formation_combo = QComboBox()
        self.formation_combo.setObjectName("encounterFormationCombo")
        for preset in FORMATION_PRESETS:
            self.formation_combo.addItem(preset.label, preset.key)
        self.formation_combo.setMinimumWidth(150)
        self.formation_combo.setToolTip(
            "Choose a reusable raid stack shape. Applying it repositions the first "
            "8 DD and first 2 healer markers, creates any that are missing, and "
            "does not delete extra markers."
        )

        formation_label = QLabel("FORMATION")
        formation_label.setProperty("sidebarHeading", True)

        apply_button = QPushButton("Apply Formation")
        apply_button.setObjectName("encounterApplyFormationButton")
        apply_button.setToolTip(
            "Apply the selected stack shape without moving bosses, tanks, portals, "
            "zones, reference points, or extra DD/healer markers."
        )
        apply_button.clicked.connect(
            lambda _checked=False: self.apply_formation(
                str(self.formation_combo.currentData() or "")
            )
        )

        insert_at = _first_spacer_index(zone_toolbar)
        zone_toolbar.insertWidget(insert_at, formation_label)
        zone_toolbar.insertWidget(insert_at + 1, self.formation_combo)
        zone_toolbar.insertWidget(insert_at + 2, apply_button)

    encounter_board.EncounterBoard.__init__ = init_with_formations
    encounter_board.EncounterBoard.apply_formation = apply_formation

    _INSTALLED = True
