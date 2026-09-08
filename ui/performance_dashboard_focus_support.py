from __future__ import annotations

"""Turn the Performance Dashboard's Quick Read card into actionable focus goals."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QSpinBox, QVBoxLayout, QWidget

from engine.config import get_data_dir
from services.performance_focus_service import (
    PerformanceBuildEvidence,
    PerformanceFocusGoal,
    PerformanceFocusStore,
    fetch_player_build_evidence,
    likely_responsibilities,
    suggest_working_target,
)
from services.performance_role_focus import desired_uptime, role_profile
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.theme.colors import Colors

_INSTALLED = False


def _store() -> PerformanceFocusStore:
    return PerformanceFocusStore(get_data_dir() / "performance_focus.json")


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())


def _target_for_result(result) -> float:
    calibrated = desired_uptime(result.name)
    if calibrated is not None:
        return float(calibrated)
    return suggest_working_target(float(result.uptime_percent))


def _current_result_map(page) -> dict[str, object]:
    snapshot = getattr(page, "_last_snapshot", None)
    if snapshot is None:
        return {}
    from ui.performance_dashboard_polish_support import _tracked_results

    names = list(getattr(page, "_tracked_effect_names", ()))
    evidence = getattr(snapshot, "BuildEvidence", PerformanceBuildEvidence())
    for name, _note in likely_responsibilities(evidence):
        if name.casefold() not in {value.casefold() for value in names}:
            names.append(name)
    return {
        result.name.casefold(): result
        for result in _tracked_results(snapshot, names)
    }


def _goal_from_result(page, result, *, evidence_note: str = "") -> PerformanceFocusGoal:
    snapshot = page._last_snapshot
    current = float(result.uptime_percent)
    return PerformanceFocusGoal(
        Name=result.name,
        TargetPercent=_target_for_result(result),
        CurrentPercent=current,
        Source="Suggested",
        ReportCode=str(getattr(snapshot, "ReportCode", "") or ""),
        FightId=str(getattr(snapshot, "FightId", "") or ""),
        FightName=str(getattr(snapshot, "FightName", "") or ""),
        ActorLabel=str(getattr(snapshot, "ActorLabel", "") or ""),
        Role=str(getattr(snapshot, "Role", "") or ""),
        EvidenceNote=evidence_note,
    )


def _pin_result(page, result, evidence_note: str = "") -> None:
    _store().upsert(_goal_from_result(page, result, evidence_note=evidence_note))
    _render_focus(page)


def _add_custom_goal(page) -> None:
    name = page.performance_focus_custom_name.text().strip()
    if not name:
        return
    target = float(page.performance_focus_custom_target.value())
    snapshot = getattr(page, "_last_snapshot", None)
    current = None
    result = _current_result_map(page).get(name.casefold())
    if result is not None and result.uptime_percent is not None:
        current = float(result.uptime_percent)

    _store().upsert(
        PerformanceFocusGoal(
            Name=name,
            TargetPercent=target,
            CurrentPercent=current,
            Source="Custom",
            ReportCode=str(getattr(snapshot, "ReportCode", "") or ""),
            FightId=str(getattr(snapshot, "FightId", "") or ""),
            FightName=str(getattr(snapshot, "FightName", "") or ""),
            ActorLabel=str(getattr(snapshot, "ActorLabel", "") or ""),
            Role=str(getattr(snapshot, "Role", "") or ""),
            EvidenceNote="User-created goal",
        )
    )
    page.performance_focus_custom_name.clear()
    _render_focus(page)


def _build_focus_card(page) -> FoundryCard:
    card = FoundryCard("Performance Focus")
    card.set_body_margins(10, 6, 10, 8)
    page.performance_focus_card = card

    page.performance_focus_intro = QLabel(
        "Suggestions are clues, not assignments. Pin only what is actually your job."
    )
    page.performance_focus_intro.setWordWrap(True)
    page.performance_focus_intro.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
    card.addWidget(page.performance_focus_intro)

    host = QWidget()
    page.performance_focus_layout = QVBoxLayout(host)
    page.performance_focus_layout.setContentsMargins(0, 0, 0, 0)
    page.performance_focus_layout.setSpacing(5)
    card.addWidget(host)

    custom_heading = QLabel("CUSTOM GOAL")
    custom_heading.setProperty("sidebarHeading", True)
    card.addWidget(custom_heading)

    custom = QHBoxLayout()
    page.performance_focus_custom_name = QLineEdit()
    page.performance_focus_custom_name.setPlaceholderText("Effect or practice goal")
    custom.addWidget(page.performance_focus_custom_name, 1)

    page.performance_focus_custom_target = QSpinBox()
    page.performance_focus_custom_target.setRange(1, 100)
    page.performance_focus_custom_target.setValue(85)
    page.performance_focus_custom_target.setSuffix("%")
    page.performance_focus_custom_target.setToolTip(
        "For non-uptime practice goals, use this as your own progress target."
    )
    custom.addWidget(page.performance_focus_custom_target)

    add = FoundryButton("+ Add Goal", role=ButtonRole.SECONDARY, compact=True)
    add.clicked.connect(lambda *_: _add_custom_goal(page))
    custom.addWidget(add)
    card.addLayout(custom)

    footer = QLabel("Pinned goals feed Raid Engine Overview → Next Raid Focus.")
    footer.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
    footer.setWordWrap(True)
    card.addWidget(footer)
    return card


def _apply_role_profile(page, snapshot) -> None:
    profile = role_profile(getattr(snapshot, "Role", ""))
    card = getattr(page, "performance_focus_card", None)
    if card is not None:
        card.set_title(profile.CardTitle)
    intro = getattr(page, "performance_focus_intro", None)
    if intro is not None:
        intro.setText(profile.Intro)

    # Role defaults are context, not assignments. Once the user explicitly adds
    # or resets tracking, preserve that choice instead of silently replacing it.
    if not getattr(page, "_tracked_effects_customized", False):
        page._tracked_effect_names = list(profile.TrackedEffects)
        from ui import performance_dashboard_polish_support as polish
        polish._render_tracking_label(page)
        polish._render_tracked_effects(page)


def _render_focus(page) -> None:
    layout = getattr(page, "performance_focus_layout", None)
    if layout is None:
        return
    _clear(layout)

    snapshot = getattr(page, "_last_snapshot", None)
    if snapshot is None:
        label = QLabel("Load a fight to build a performance focus list.")
        label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(label)
        return

    result_map = _current_result_map(page)
    pinned = {goal.Name.casefold(): goal for goal in _store().load()}
    evidence = getattr(snapshot, "BuildEvidence", PerformanceBuildEvidence())
    inferred = {name.casefold(): note for name, note in likely_responsibilities(evidence)}
    role = str(getattr(snapshot, "Role", "") or "").casefold()
    custom_tracking = bool(getattr(page, "_tracked_effects_customized", False))

    candidates = []
    for key, result in result_map.items():
        if result.uptime_percent is None:
            continue
        explicit = key in {
            str(name or "").strip().casefold()
            for name in getattr(page, "_tracked_effect_names", ())
        }

        # Healer tracking remains intentionally broad because support coverage is
        # the role's central job. DPS/tank role defaults are contextual until the
        # build evidence or the user explicitly marks an effect as their concern.
        personally_relevant = key in inferred or (
            explicit and ("heal" in role or custom_tracking)
        )
        if not personally_relevant:
            continue
        candidates.append((float(result.uptime_percent), result, inferred.get(key, "Tracked by you")))
    candidates.sort(key=lambda row: row[0])

    if evidence.GearSets or evidence.Abilities:
        bits = []
        if evidence.ClassName:
            bits.append(evidence.ClassName)
        if evidence.GearSets:
            bits.append("gear: " + ", ".join(evidence.GearSets[:3]))
        build_line = QLabel("ESO Logs build evidence: " + " • ".join(bits))
        build_line.setWordWrap(True)
        build_line.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(build_line)

    for _pct, result, note in candidates[:4]:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 1, 0, 1)
        row_layout.setSpacing(7)

        target = _target_for_result(result)
        target_note = "BFF calibrated target" if desired_uptime(result.name) is not None else "next-step target"
        text = QLabel(
            f"△  {result.name}  {result.uptime_percent:.1f}%  →  {target:.0f}%\n"
            f"     {note} • {target_note}"
        )
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {Colors.TEXT};")
        row_layout.addWidget(text, 1)

        is_pinned = result.name.casefold() in pinned
        button = FoundryButton(
            "Pinned" if is_pinned else "☆ Pin",
            role=ButtonRole.SECONDARY,
            compact=True,
        )
        button.setEnabled(not is_pinned)
        button.clicked.connect(
            lambda _checked=False, owner=page, value=result, reason=note: _pin_result(
                owner, value, reason
            )
        )
        row_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(row)

    if not candidates:
        if "dps" in role:
            message = (
                "No build-owned measurable uptime is weak enough to surface yet. "
                "The raid buffs above remain useful context; add a custom goal for rotation, DoT, execute, or weave work."
            )
        elif "tank" in role:
            message = (
                "No source-backed tank responsibility is measurable in this effect set yet. "
                "Add a custom goal for taunt, blocking, positioning, or another mechanic until event-level tank metrics are wired."
            )
        else:
            message = (
                "No measurable tracked uptimes are available yet. Add a custom goal below if the thing you want to improve is not an aura percentage."
            )
        label = QLabel(message)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(label)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from services import performance_dashboard_service as service_module
    from ui import performance_dashboard_polish_support as polish
    from widgets.performance_dashboard import PerformanceDashboard

    # _build_ui_clean resolves this module-level helper when a dashboard is
    # constructed, so replacing it here cleanly swaps Quick Read for Focus.
    polish._build_quick_read_card = _build_focus_card

    # Mark hand-edited tracking so role defaults never erase the user's choices.
    original_add_tracked = polish._add_tracked_effect
    original_reset_tracked = polish._reset_tracked_effects

    def add_tracked_with_role_memory(page):
        page._tracked_effects_customized = True
        original_add_tracked(page)

    def reset_tracked_for_role(page):
        page._tracked_effects_customized = False
        snapshot = getattr(page, "_last_snapshot", None)
        if snapshot is not None:
            page._tracked_effect_names = list(role_profile(snapshot.Role).TrackedEffects)
            polish._render_tracking_label(page)
            polish._render_tracked_effects(page)
            return
        original_reset_tracked(page)

    polish._add_tracked_effect = add_tracked_with_role_memory
    polish._reset_tracked_effects = reset_tracked_for_role

    original_snapshot = service_module.PerformanceDashboardService.build_snapshot
    original_show = PerformanceDashboard.show_snapshot

    def build_snapshot_with_build_evidence(self, *args, **kwargs):
        snapshot = original_snapshot(self, *args, **kwargs)
        snapshot.BuildEvidence = PerformanceBuildEvidence(Role=str(snapshot.Role or ""))
        snapshot.BuildEvidenceError = ""
        try:
            summary = self.capability_service.fetch_fight_summary(
                snapshot.ReportCode, int(snapshot.FightId)
            )
            snapshot.BuildEvidence = fetch_player_build_evidence(
                self.client,
                report_code=snapshot.ReportCode,
                fight_id=int(snapshot.FightId),
                actor_id=int(snapshot.ActorId),
                start_ms=float(summary["start_time"]),
                end_ms=float(summary["end_time"]),
                role=snapshot.Role,
            )
        except Exception as exc:
            snapshot.BuildEvidenceError = str(exc)
        return snapshot

    def show_snapshot_with_focus(self, snapshot):
        original_show(self, snapshot)
        _apply_role_profile(self, snapshot)
        _render_focus(self)

    service_module.PerformanceDashboardService.build_snapshot = build_snapshot_with_build_evidence
    PerformanceDashboard.show_snapshot = show_snapshot_with_focus
    _INSTALLED = True
