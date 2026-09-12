from __future__ import annotations

"""Connect completed Rotation plans to their canonical saved builds.

The Rotation page owns generation.  This layer only persists an already-rendered
RotationPlan and presents that saved artifact on the Builds workspace.  It never
generates, repairs, or infers rotation evidence while saving.
"""

from typing import Any

from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.build_rotation_artifact_service import (
    BuildRotationArtifactService,
    jsonable,
    resolve_canonical_build_id,
)
from ui.components.foundry_card import FoundryCard

_INSTALLED = False


def _artifact_service() -> BuildRotationArtifactService:
    return BuildRotationArtifactService(get_data_dir() / "build_rotations.json")


def _build_id_for_page(page, build) -> str | None:
    return resolve_canonical_build_id(
        page.build_service.canonical.catalog_service,
        build,
    )


def _policy(page, name: str) -> dict[str, Any]:
    resolver = getattr(page, name, None)
    if not callable(resolver):
        return {}
    try:
        value = resolver()
    except (TypeError, ValueError):
        return {}
    return dict(value) if isinstance(value, dict) else {}


def _rotation_artifact(page) -> dict[str, Any]:
    plan = page.rotation_plan
    if plan is None or not tuple(getattr(plan, "actions", ()) or ()):
        raise ValueError("Generate a completed rotation before saving it to the build.")

    setup = dict(page.rotation_settings())
    setup.update(_policy(page, "canonical_threshold_projection_policy"))
    setup.update(_policy(page, "canonical_dd_evaluation_policy"))

    recovery = _policy(page, "canonical_recovery_policy")
    if recovery:
        setup["recovery_resource"] = recovery.get("resource")
        setup["recovery_trigger_fraction"] = recovery.get("trigger_fraction")

    selected_encounter = getattr(page, "selected_encounter_id", None)
    encounter_id = selected_encounter() if callable(selected_encounter) else None

    payload = jsonable(plan)
    payload["artifact_schema_version"] = 1
    payload["encounter_id"] = str(encounter_id or "")
    payload["setup"] = jsonable(setup)
    return payload


def _find_tab(tabs, title: str) -> int:
    wanted = str(title or "").strip().casefold()
    for index in range(tabs.count()):
        if str(tabs.tabText(index) or "").strip().casefold() == wanted:
            return index
    return -1


def _build_rotation_workspace(page) -> QWidget:
    workspace = QWidget()
    root = QVBoxLayout(workspace)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(10)

    summary_card = FoundryCard("Saved Rotation", "◇").set_watermark("compass", 0.035)
    page.saved_rotation_summary = QLabel()
    page.saved_rotation_summary.setWordWrap(True)
    summary_card.addWidget(page.saved_rotation_summary)
    root.addWidget(summary_card)

    setup_card = FoundryCard("Rotation Setup", "◆").set_watermark("compass", 0.03)
    page.saved_rotation_setup = QLabel()
    page.saved_rotation_setup.setWordWrap(True)
    page.saved_rotation_setup.setProperty("muted", True)
    setup_card.addWidget(page.saved_rotation_setup)
    root.addWidget(setup_card)

    timeline_card = FoundryCard("Rotation Timeline", "☷").set_watermark("compass", 0.03)
    page.saved_rotation_table = QTableWidget(0, 5)
    page.saved_rotation_table.setHorizontalHeaderLabels(
        ["Time", "Bar", "Action", "Type", "Notes"]
    )
    page.saved_rotation_table.verticalHeader().setVisible(False)
    page.saved_rotation_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    page.saved_rotation_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    page.saved_rotation_table.horizontalHeader().setStretchLastSection(True)
    page.saved_rotation_table.setMinimumHeight(320)
    timeline_card.addWidget(page.saved_rotation_table)
    root.addWidget(timeline_card, 1)
    return workspace


def _selected_build(page):
    index = getattr(page, "selected_index", -1)
    if isinstance(index, int) and 0 <= index < len(page.roster.Members):
        return page.roster.Members[index]
    return None


def _fallback_build_tab(page) -> None:
    index = _find_tab(page.build_tabs, "Builds")
    if index < 0:
        index = 0
    page.build_tabs.setCurrentIndex(index)


def _display_number(value, *, suffix: str = "") -> str:
    if value is None or value == "":
        return "Not set"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    text = f"{number:,.0f}" if number.is_integer() else f"{number:g}"
    return f"{text}{suffix}"


def _refresh_build_rotation(page) -> None:
    if not hasattr(page, "saved_rotation_workspace") or not hasattr(page, "build_tabs"):
        return

    tab_index = page.build_tabs.indexOf(page.saved_rotation_workspace)
    if tab_index < 0:
        return

    build = _selected_build(page)
    build_id = _build_id_for_page(page, build) if build is not None else None
    artifact = page.build_rotation_artifacts.get_rotation(build_id or "")
    actions = list(artifact.get("actions") or []) if isinstance(artifact, dict) else []
    visible = bool(build_id and artifact and actions)

    if not visible:
        if page.build_tabs.currentWidget() is page.saved_rotation_workspace:
            _fallback_build_tab(page)
        page.build_tabs.setTabVisible(tab_index, False)
        page.saved_rotation_table.setRowCount(0)
        page.saved_rotation_summary.setText("")
        page.saved_rotation_setup.setText("")
        return

    page.build_tabs.setTabVisible(tab_index, True)
    setup = artifact.get("setup") if isinstance(artifact.get("setup"), dict) else {}
    character = str(artifact.get("character_name") or getattr(build, "Name", "") or "Unnamed Character")
    build_name = str(artifact.get("build_name") or getattr(build, "BuildName", "") or "Current Build")
    role = str(artifact.get("role") or getattr(build, "Role", "") or "Unspecified")
    rotation_type = str(artifact.get("rotation_type") or "Unspecified")
    duration = float(artifact.get("duration_seconds") or 0.0)
    encounter_id = str(artifact.get("encounter_id") or "").strip()
    potion = str(setup.get("potion") or "").strip()

    summary_lines = [
        f"{character} • {build_name}",
        f"{role} • {rotation_type} • {duration:g}s",
        f"Actions: {len(actions)}",
    ]
    if encounter_id:
        summary_lines.append(f"Encounter: {encounter_id}")
    page.saved_rotation_summary.setText("\n".join(summary_lines))

    recovery_resource = str(setup.get("recovery_resource") or "Not set").title()
    recovery_trigger = setup.get("recovery_trigger_fraction")
    recovery_trigger_text = (
        "Not set"
        if recovery_trigger is None
        else f"{float(recovery_trigger) * 100:g}%"
    )
    setup_lines = [
        f"Execute: {_display_number(setup.get('execute_percent'), suffix='%')}",
        f"Target: {setup.get('target_type') or 'Not set'}",
        f"Raid DPS: {_display_number(setup.get('raid_dps'))}",
        f"Target resistance: {_display_number(setup.get('target_resistance'))}",
        f"Recovery: {recovery_resource} at {recovery_trigger_text}",
        f"Potion: {potion or 'None'}",
        f"Potion on cooldown: {'Yes' if setup.get('potion_on_cooldown') else 'No'}",
    ]
    page.saved_rotation_setup.setText("\n".join(setup_lines))

    page.saved_rotation_table.setRowCount(0)
    for action in actions:
        if not isinstance(action, dict):
            continue
        row = page.saved_rotation_table.rowCount()
        page.saved_rotation_table.insertRow(row)
        time_seconds = float(action.get("time_seconds") or 0.0)
        kind = str(action.get("kind") or "").replace("_", " ").title()
        values = (
            f"{time_seconds:.1f}s",
            str(action.get("bar") or "—").title(),
            str(action.get("name") or kind or "—"),
            kind or "—",
            str(action.get("notes") or ""),
        )
        for column, value in enumerate(values):
            page.saved_rotation_table.setItem(row, column, QTableWidgetItem(value))


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage
    from ui.themed_builds_page import BuildsPage

    rotation_init = CanonicalRotationDashboardPage.__init__
    rotation_set_plan = CanonicalRotationDashboardPage.set_rotation_plan
    rotation_clear_plan = CanonicalRotationDashboardPage.clear_rotation_plan

    def rotation_init_with_build_save(self, *args, **kwargs) -> None:
        rotation_init(self, *args, **kwargs)
        self.build_rotation_artifacts = _artifact_service()
        self.save_rotation_to_build_button = QPushButton("Save Rotation to Build")
        self.save_rotation_to_build_button.setProperty("primary", True)
        self.save_rotation_to_build_button.setEnabled(bool(self.rotation_plan and self.rotation_plan.actions))
        self.save_rotation_to_build_button.setToolTip(
            "Save the currently completed RotationPlan to this exact canonical build. "
            "Saving again replaces that build's previous saved rotation."
        )

        def save_current_rotation() -> None:
            build = self._selected_build()
            if build is None:
                self.status.warning("Select a saved build before saving a rotation.")
                return
            if self.rotation_plan is None or not self.rotation_plan.actions:
                self.status.warning("Generate a completed rotation before saving it to the build.")
                return
            build_id = _build_id_for_page(self, build)
            if not build_id:
                self.status.warning(
                    "This saved build could not be resolved to one canonical build identity; rotation was not saved."
                )
                return
            try:
                self.build_rotation_artifacts.save_rotation(
                    build_id=build_id,
                    artifact=_rotation_artifact(self),
                )
            except (OSError, ValueError) as exc:
                self.status.error(f"Save rotation to build failed: {exc}")
                return
            character = str(getattr(build, "Name", "") or "Unnamed Character")
            build_name = str(getattr(build, "BuildName", "") or "Current Build")
            self.status.success(
                f"Saved rotation to {character} • {build_name}. It is now available on the Build page."
            )

        self.save_rotation_to_build_button.clicked.connect(save_current_rotation)
        self.header.add_context_widget(self.save_rotation_to_build_button)

    def set_plan_with_build_save(self, plan) -> None:
        rotation_set_plan(self, plan)
        if hasattr(self, "save_rotation_to_build_button"):
            self.save_rotation_to_build_button.setEnabled(bool(plan and plan.actions))

    def clear_plan_with_build_save(self, *args, **kwargs) -> None:
        rotation_clear_plan(self, *args, **kwargs)
        if hasattr(self, "save_rotation_to_build_button"):
            self.save_rotation_to_build_button.setEnabled(False)

    CanonicalRotationDashboardPage.__init__ = rotation_init_with_build_save
    CanonicalRotationDashboardPage.set_rotation_plan = set_plan_with_build_save
    CanonicalRotationDashboardPage.clear_rotation_plan = clear_plan_with_build_save

    builds_build_ui = BuildsPage._build_ui
    builds_select_member = BuildsPage._select_member
    builds_show_event = getattr(BuildsPage, "showEvent")

    def builds_ui_with_rotation_tab(self) -> None:
        builds_build_ui(self)
        self.build_rotation_artifacts = _artifact_service()
        self.saved_rotation_workspace = _build_rotation_workspace(self)
        rotation_index = self.build_tabs.addTab(
            self.saved_rotation_workspace,
            "Rotation",
        )
        self.build_tabs.setTabToolTip(
            rotation_index,
            "Completed rotation saved from Raid Engine • Rotations for this exact build.",
        )
        self.build_tabs.setTabVisible(rotation_index, False)

    def select_member_with_rotation(self, row: int) -> None:
        builds_select_member(self, row)
        _refresh_build_rotation(self)

    def show_event_with_rotation(self, event) -> None:
        builds_show_event(self, event)
        _refresh_build_rotation(self)

    BuildsPage._build_ui = builds_ui_with_rotation_tab
    BuildsPage._select_member = select_member_with_rotation
    BuildsPage.showEvent = show_event_with_rotation

    _INSTALLED = True


__all__ = ["install"]
