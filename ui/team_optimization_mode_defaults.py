from __future__ import annotations

from dataclasses import dataclass

from minmax.optimization_mode import OptimizationMode


_INSTALLED = False
_ORIGINAL_BUILD_CONSTRAINTS = None
_ORIGINAL_MODE_CHANGED = None


@dataclass(frozen=True)
class OptimizationModeDefaults:
    team_source: str
    lock_players: bool
    lock_roles: bool
    lock_classes: bool
    keep_current_builds: bool
    allow_role_swap: bool
    allow_gear_changes: bool


_MODE_DEFAULTS = {
    OptimizationMode.AUDIT: OptimizationModeDefaults(
        team_source="Saved Players Only",
        lock_players=True,
        lock_roles=True,
        lock_classes=True,
        keep_current_builds=True,
        allow_role_swap=False,
        allow_gear_changes=False,
    ),
    OptimizationMode.BUILD: OptimizationModeDefaults(
        team_source="Hybrid: Players + Recruitment",
        lock_players=False,
        lock_roles=False,
        lock_classes=False,
        keep_current_builds=False,
        allow_role_swap=True,
        allow_gear_changes=True,
    ),
    OptimizationMode.RECRUIT: OptimizationModeDefaults(
        team_source="Recruitment Plan Only",
        lock_players=False,
        lock_roles=False,
        lock_classes=False,
        keep_current_builds=False,
        allow_role_swap=True,
        allow_gear_changes=True,
    ),
    OptimizationMode.COMPARE: OptimizationModeDefaults(
        team_source="Hybrid: Players + Recruitment",
        lock_players=True,
        lock_roles=True,
        lock_classes=True,
        keep_current_builds=True,
        allow_role_swap=False,
        allow_gear_changes=False,
    ),
}


def defaults_for_mode(mode: OptimizationMode) -> OptimizationModeDefaults:
    return _MODE_DEFAULTS[mode]


def _capture_state(page) -> dict[str, object]:
    return {
        "team_source": page.team_source_combo.currentText(),
        "constraints": {
            name: box.isChecked()
            for name, box in page.constraint_boxes.items()
        },
    }


def _apply_state(page, state: dict[str, object]) -> None:
    source = str(state.get("team_source") or "").strip()
    source_index = page.team_source_combo.findText(source)
    if source_index >= 0:
        blocked = page.team_source_combo.blockSignals(True)
        try:
            page.team_source_combo.setCurrentIndex(source_index)
        finally:
            page.team_source_combo.blockSignals(blocked)

    constraints = state.get("constraints")
    if isinstance(constraints, dict):
        for name, checked in constraints.items():
            box = page.constraint_boxes.get(str(name))
            if box is not None:
                box.setChecked(bool(checked))


def _preset_state(mode: OptimizationMode) -> dict[str, object]:
    preset = defaults_for_mode(mode)
    return {
        "team_source": preset.team_source,
        "constraints": {
            "Lock Players": preset.lock_players,
            "Lock Roles": preset.lock_roles,
            "Lock Classes": preset.lock_classes,
            "Keep Current Builds": preset.keep_current_builds,
            "Allow Role Swap": preset.allow_role_swap,
            "Allow Gear Changes": preset.allow_gear_changes,
        },
    }


def _set_help_text(page) -> None:
    page.team_source_combo.setToolTip(
        "A sensible source is selected automatically for each Optimization mode. "
        "You can change it at any time."
    )
    hints = {
        "Lock Players": (
            "Keep the exact players currently selected in Team A. In Build Best Team, "
            "turn this on when the people you already selected must stay in the team."
        ),
        "Lock Roles": "Prevent the prescription from recommending role changes.",
        "Lock Classes": "Prevent class recommendations from changing for prescribed chairs.",
        "Keep Current Builds": (
            "Keep current saved builds. Turn this off when you want BFF to prescribe "
            "gear, skills, Mundus, CP, food, potion, and other build dimensions."
        ),
        "Allow Role Swap": "Allow role changes when the current mode and evidence support them.",
        "Allow Gear Changes": "Allow gear-set and equipment recommendations.",
    }
    for name, text in hints.items():
        box = page.constraint_boxes.get(name)
        if box is not None:
            box.setToolTip(text)


def _build_constraints_with_mode_defaults(self) -> None:
    assert _ORIGINAL_BUILD_CONSTRAINTS is not None
    _ORIGINAL_BUILD_CONSTRAINTS(self)

    self._optimization_mode_states = {}
    self._optimization_mode_active_mode = self._current_mode()
    _apply_state(
        self,
        _preset_state(self._optimization_mode_active_mode),
    )
    _set_help_text(self)


def _optimization_mode_changed_with_defaults(self, index: int) -> None:
    assert _ORIGINAL_MODE_CHANGED is not None

    previous = getattr(self, "_optimization_mode_active_mode", None)
    states = getattr(self, "_optimization_mode_states", None)
    if isinstance(states, dict) and previous is not None and self.constraint_boxes:
        states[previous] = _capture_state(self)

    mode = self._current_mode()
    if not isinstance(states, dict):
        states = {}
        self._optimization_mode_states = states
    state = states.get(mode)
    if state is None:
        state = _preset_state(mode)
    _apply_state(self, state)
    self._optimization_mode_active_mode = mode

    _ORIGINAL_MODE_CHANGED(self, index)


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_CONSTRAINTS, _ORIGINAL_MODE_CHANGED
    if _INSTALLED:
        return

    from ui.optimization_page import OptimizationPage

    _ORIGINAL_BUILD_CONSTRAINTS = OptimizationPage._build_constraints
    _ORIGINAL_MODE_CHANGED = OptimizationPage._optimization_mode_changed
    OptimizationPage._build_constraints = _build_constraints_with_mode_defaults
    OptimizationPage._optimization_mode_changed = _optimization_mode_changed_with_defaults
    _INSTALLED = True
