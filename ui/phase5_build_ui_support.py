from __future__ import annotations

"""Phase 5 Builds UI integration.

Keeps character-owned progression separate from individual build payloads while
adding small quality-of-life actions to the existing BuildEditor.
"""

from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from models.build_model import PlayerBuild
from services.character_progression_service import CharacterProgressionService
from ui.components.foundry_button import ButtonRole, FoundryButton

_INSTALLED = False

_DISCIPLINE_NAMES = {
    1: "The Mage",
    2: "The Warrior",
    3: "The Thief",
}


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class CharacterProgressionDialog(QDialog):
    """Edit permanent progression owned by one canonical character."""

    def __init__(self, *, reference, character: dict, parent=None) -> None:
        super().__init__(parent)
        self.reference = reference
        self.character = dict(character or {})
        self.eso_class = _clean(self.character.get("eso_class"))
        self._owned = {
            _clean(name).casefold()
            for name in self.character.get("owned_skill_lines", [])
            if _clean(name)
        }
        self._stored_passives = {
            _clean(name).casefold(): _int(rank)
            for name, rank in dict(self.character.get("passive_ranks") or {}).items()
            if _clean(name)
        }
        self._stored_cp = {
            _clean(name).casefold(): _int(points)
            for name, points in dict(self.character.get("passive_cp_points") or {}).items()
            if _clean(name)
        }
        self._line_checks: dict[str, QCheckBox] = {}
        self._passive_spins: dict[str, tuple[str, QSpinBox]] = {}
        self._cp_spins: dict[str, tuple[str, QSpinBox]] = {}

        name = _clean(self.character.get("name")) or "Character"
        self.setWindowTitle(f"Character Progression — {name}")
        self.resize(900, 760)
        self.setMinimumSize(700, 520)

        root = QVBoxLayout(self)
        explanation = QLabel(
            "These choices belong to the character and are shared by every build. "
            "Class skill lines are available automatically, but passive ranks are never assumed purchased."
        )
        explanation.setWordWrap(True)
        explanation.setProperty("pageSubtitle", True)
        root.addWidget(explanation)

        tabs = QTabWidget()
        tabs.addTab(self._scrollable(self._skill_passive_tab()), "Skill Passives")
        tabs.addTab(self._scrollable(self._passive_cp_tab()), "Passive Champion Points")
        root.addWidget(tabs, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = FoundryButton("Cancel", role=ButtonRole.SECONDARY, compact=True)
        save = FoundryButton("Save Character Progression", role=ButtonRole.SUCCESS, compact=True)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(save)
        root.addLayout(actions)

    @staticmethod
    def _scrollable(widget: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        area.setWidget(widget)
        return area

    def _passive_rows_by_line(self) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = defaultdict(list)
        seen: set[tuple[str, str]] = set()
        for skill in self.reference.list_skills():
            if not isinstance(skill, dict):
                continue
            if _int(skill.get("is_player")) != 1 or _int(skill.get("is_passive")) != 1:
                continue
            owner = _clean(skill.get("class_type"))
            if owner and owner.casefold() != self.eso_class.casefold():
                continue
            line = _clean(skill.get("skill_line"))
            name = _clean(skill.get("name"))
            if not line or not name:
                continue
            key = (line.casefold(), name.casefold())
            if key in seen:
                continue
            seen.add(key)
            grouped[line].append(skill)
        for rows in grouped.values():
            rows.sort(key=lambda value: _clean(value.get("name")).casefold())
        return dict(sorted(grouped.items(), key=lambda item: item[0].casefold()))

    def _skill_passive_tab(self) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)

        note = QLabel(
            "Expand a line to record the ranks this character actually purchased. "
            "Buy All sets every passive in that line to its database-backed maximum rank."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        toolbox = QToolBox()
        for line, rows in self._passive_rows_by_line().items():
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(12, 10, 12, 10)
            page_layout.setSpacing(6)

            owner_values = {_clean(row.get("class_type")) for row in rows if _clean(row.get("class_type"))}
            class_line = bool(owner_values) and self.eso_class in owner_values

            header = QHBoxLayout()
            if class_line:
                access = QLabel(f"{self.eso_class} class line")
                access.setProperty("cardBadge", True)
                header.addWidget(access)
            else:
                check = QCheckBox("Skill line unlocked")
                check.setChecked(line.casefold() in self._owned)
                self._line_checks[line] = check
                header.addWidget(check)
            header.addStretch()
            buy_all = FoundryButton("Buy All", role=ButtonRole.SECONDARY, compact=True)
            clear = FoundryButton("Clear", role=ButtonRole.GHOST, compact=True)
            header.addWidget(buy_all)
            header.addWidget(clear)
            page_layout.addLayout(header)

            grid = QGridLayout()
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(5)
            line_spins: list[QSpinBox] = []
            for row_index, skill in enumerate(rows):
                name = _clean(skill.get("name"))
                maximum = max(1, _int(skill.get("rank"), 1))
                spin = QSpinBox()
                spin.setRange(0, maximum)
                spin.setSuffix(f" / {maximum}")
                spin.setValue(max(0, min(maximum, self._stored_passives.get(name.casefold(), 0))))
                spin.setFixedWidth(92)
                description = _clean(skill.get("description"))
                label = QLabel(name)
                if description:
                    label.setToolTip(description)
                    spin.setToolTip(description)
                grid.addWidget(label, row_index, 0)
                grid.addWidget(spin, row_index, 1)
                self._passive_spins[name.casefold()] = (name, spin)
                line_spins.append(spin)
            grid.setColumnStretch(0, 1)
            page_layout.addLayout(grid)

            def buy_line(*_args, spins=line_spins, skill_line=line, is_class=class_line) -> None:
                if not is_class and skill_line in self._line_checks:
                    self._line_checks[skill_line].setChecked(True)
                for spin in spins:
                    spin.setValue(spin.maximum())

            def clear_line(*_args, spins=line_spins) -> None:
                for spin in spins:
                    spin.setValue(0)

            buy_all.clicked.connect(buy_line)
            clear.clicked.connect(clear_line)
            toolbox.addItem(page, line)

        layout.addWidget(toolbox)
        layout.addStretch()
        return host

    def _passive_cp_tab(self) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)

        note = QLabel(
            "Only non-slottable Champion stars appear here. Record the points actually purchased; "
            "the 12 slotted stars remain build-specific in the normal Champion Points editor."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        grouped: dict[int, list[dict]] = defaultdict(list)
        for cp in self.reference.list_champion_points():
            if not isinstance(cp, dict) or _int(cp.get("skill_type"), -1) != 0:
                continue
            name = _clean(cp.get("name"))
            if name:
                grouped[_int(cp.get("discipline_id"))].append(cp)

        toolbox = QToolBox()
        for discipline in sorted(grouped):
            page = QWidget()
            grid = QGridLayout(page)
            grid.setContentsMargins(12, 10, 12, 10)
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(5)
            rows = sorted(grouped[discipline], key=lambda value: _clean(value.get("name")).casefold())
            for row_index, cp in enumerate(rows):
                name = _clean(cp.get("name"))
                maximum = max(1, _int(cp.get("max_points"), 1))
                spin = QSpinBox()
                spin.setRange(0, maximum)
                spin.setSuffix(f" / {maximum}")
                spin.setValue(max(0, min(maximum, self._stored_cp.get(name.casefold(), 0))))
                spin.setFixedWidth(100)
                description = _clean(cp.get("description"))
                label = QLabel(name)
                if description:
                    label.setToolTip(description)
                    spin.setToolTip(description)
                grid.addWidget(label, row_index, 0)
                grid.addWidget(spin, row_index, 1)
                self._cp_spins[name.casefold()] = (name, spin)
            grid.setColumnStretch(0, 1)
            toolbox.addItem(page, _DISCIPLINE_NAMES.get(discipline, f"Discipline {discipline}"))

        layout.addWidget(toolbox)
        layout.addStretch()
        return host

    @property
    def owned_skill_lines(self) -> list[str]:
        return [line for line, check in self._line_checks.items() if check.isChecked()]

    @property
    def passive_ranks(self) -> dict[str, int]:
        return {
            name: spin.value()
            for name, spin in self._passive_spins.values()
            if spin.value() > 0
        }

    @property
    def passive_cp_points(self) -> dict[str, int]:
        return {
            name: spin.value()
            for name, spin in self._cp_spins.values()
            if spin.value() > 0
        }


def _finish_endgame_gear(editor) -> None:
    """Set every populated gear slot to CP160 Legendary without changing mechanics."""
    for row in getattr(editor, "gear_rows", {}).values():
        slot = row.value
        if slot.is_empty:
            continue
        row.quality_combo.setCurrentText("Gold")
        row.level_combo.setCurrentText("CP160")


def _character_id_for_page(page, build: PlayerBuild) -> str | None:
    direct = _clean(getattr(build, "CharacterId", ""))
    if direct:
        return direct
    progression = CharacterProgressionService(page.build_service.canonical.catalog_service)
    found = progression.find_character_id(name=build.Name, gamertag=build.Gamertag)
    if found:
        return found
    page.build_service.canonical.sync_from_roster(page.roster)
    return progression.find_character_id(name=build.Name, gamertag=build.Gamertag)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from widgets.build_editor import BuildEditor

    # ---- BuildEditor: one-click endgame gear finishing ------------------
    original_gear_card = BuildEditor._build_gear_card

    def gear_card_with_finisher(self):
        card = original_gear_card(self)
        button = FoundryButton("✦ FINISH ENDGAME GEAR", role=ButtonRole.PRIMARY, compact=True)
        button.setToolTip("Set every populated gear slot to CP160 and Gold. Sets, traits, enchants, weights, and weapon types are unchanged.")
        button.clicked.connect(lambda *_: _finish_endgame_gear(self))
        card.set_header_action(button)
        return card

    BuildEditor._build_gear_card = gear_card_with_finisher
    BuildEditor.finish_endgame_gear = _finish_endgame_gear

    # ---- Builds page: compact character progression access --------------
    original_identity_header = BuildsPage._identity_header

    def identity_header_with_progression(self, name: str, role: str, build: PlayerBuild) -> QWidget:
        frame = original_identity_header(self, name, role, build)
        layout = frame.layout()
        if layout is not None:
            button = FoundryButton("Character Progression", role=ButtonRole.SECONDARY, compact=True)
            button.setToolTip("Skill-line access, purchased passive ranks, and passive Champion Points shared by every build for this character.")
            button.clicked.connect(lambda *_: self._edit_character_progression(build))
            layout.addWidget(button)
        return frame

    def edit_character_progression(self, build: PlayerBuild) -> None:
        character_id = _character_id_for_page(self, build)
        if not character_id:
            self.status.error("Character progression could not resolve a canonical character identity.")
            return
        catalog_service = self.build_service.canonical.catalog_service
        character = catalog_service.get_character(character_id)
        if character is None:
            self.status.error("Canonical character record was not found.")
            return
        dialog = CharacterProgressionDialog(reference=self.reference, character=character, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        service = CharacterProgressionService(catalog_service)
        saved = service.save(
            character_id=character_id,
            owned_skill_lines=dialog.owned_skill_lines,
            passive_ranks=dialog.passive_ranks,
            passive_cp_points=dialog.passive_cp_points,
        )
        if saved is None:
            self.status.error("Character progression could not be saved.")
            return
        self.status.success("Character progression saved. All builds for this character share it.")
        self._refresh_detail()

    BuildsPage._identity_header = identity_header_with_progression
    BuildsPage._edit_character_progression = edit_character_progression

    _INSTALLED = True
