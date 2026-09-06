from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from engine.config import get_data_dir
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import GeneratedRosterPlanService
from services.roster_recruit_adoption_service import RosterRecruitAdoptionService
from services.roster_service import RosterService


_INSTALLED = False
_ORIGINAL_INIT = None


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _selected_plan(page):
    service = getattr(page, "generated_plan_service", None)
    combo = getattr(page, "generated_plan_combo", None)
    if service is None:
        return None
    name = combo.currentText().strip() if combo is not None else ""
    return service.load_plan(name) if name else service.latest_plan()


def _selected_slot(page):
    if getattr(page, "view_combo", None) is None:
        return None
    if page.view_combo.currentText().strip() != "Generated Team":
        return None
    row = page.assignment_table.currentRow()
    if row < 0:
        return None
    slot_item = page.assignment_table.item(row, 1)
    slot_name = _clean(slot_item.text() if slot_item is not None else "")
    plan = _selected_plan(page)
    if plan is None or not slot_name:
        return None
    return next(
        (
            slot
            for slot in plan.slots
            if _clean(slot.slot_name).casefold() == slot_name.casefold()
        ),
        None,
    )


def _update_assign_button(page, *_args) -> None:
    button = getattr(page, "assign_recruit_button", None)
    if button is None:
        return
    slot = _selected_slot(page)
    enabled = slot is not None and slot.kind != "saved"
    button.setEnabled(enabled)
    if enabled:
        button.setToolTip(
            f"Assign a real roster player/build to {slot.slot_name} without changing other builds."
        )
    else:
        button.setToolTip("Select a Recruitment Needed row in Generated Team.")


def _member_label(member) -> str:
    player = _clean(member.PlayerName) or "Unnamed Player"
    character = _clean(member.CharacterName)
    return f"{player} • {character}" if character else player


def _build_label(build) -> str:
    name = _clean(getattr(build, "BuildName", "")) or "Current Build"
    eso_class = _clean(getattr(build, "EsoClass", ""))
    return f"{name} • {eso_class}" if eso_class else name


def _show_recruit_dialog(page, *_args) -> None:
    plan = _selected_plan(page)
    slot = _selected_slot(page)
    if plan is None or slot is None or slot.kind == "saved":
        page.status.info("Select a Recruitment Needed row in Generated Team first.")
        return

    service = page._roster_recruit_adoption_service
    members = [
        member
        for member in page._roster_recruit_roster_service.list_members()
        if _clean(member.Status).casefold() != "inactive"
    ]
    if not members:
        page.status.warning("Roster has no active or bench players available to assign.")
        return

    dialog = QDialog(page)
    dialog.setWindowTitle(f"Assign Recruit • {slot.slot_name}")
    dialog.resize(560, 360)
    root = QVBoxLayout(dialog)

    prescription = QLabel(
        "\n".join(
            (
                f"CHAIR: {slot.slot_name}",
                f"PRESCRIBED CLASS: {_clean(slot.eso_class) or 'Any class'}",
                f"PRESCRIBED BUILD: {_clean(slot.build_name) or 'Open requirement'}",
                "The original prescription will remain stored after assignment for later encounter-aware comparison.",
            )
        )
    )
    prescription.setWordWrap(True)
    root.addWidget(prescription)

    form = QFormLayout()
    player_combo = QComboBox()
    for member in members:
        player_combo.addItem(_member_label(member), member.Id)
    form.addRow("ROSTER PLAYER", player_combo)

    mode_combo = QComboBox()
    mode_combo.addItem("Use existing saved build", "existing")
    mode_combo.addItem("Create new draft from prescribed setup", "adopt")
    form.addRow("ASSIGNMENT", mode_combo)

    build_combo = QComboBox()
    form.addRow("SAVED / BASE BUILD", build_combo)

    new_name = QLineEdit()
    new_name.setPlaceholderText("e.g. GH Healer")
    form.addRow("NEW BUILD NAME", new_name)
    root.addLayout(form)

    boundary = QLabel(
        "Draft adoption clones the chosen saved build and applies only fully specified facts. "
        "Gear-set lists and observed abilities are kept as structured prescription evidence until exact slots and bar placement are known."
    )
    boundary.setWordWrap(True)
    root.addWidget(boundary)

    def refresh_builds() -> None:
        member_id = player_combo.currentData()
        build_combo.clear()
        if member_id is None:
            return
        for build in service.available_builds(int(member_id)):
            build_combo.addItem(_build_label(build), _clean(build.BuildName))

    def refresh_mode() -> None:
        adopting = mode_combo.currentData() == "adopt"
        new_name.setEnabled(adopting)
        boundary.setVisible(adopting)

    player_combo.currentIndexChanged.connect(lambda *_: refresh_builds())
    mode_combo.currentIndexChanged.connect(lambda *_: refresh_mode())
    refresh_builds()
    refresh_mode()

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    root.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    member_id = player_combo.currentData()
    build_name = _clean(build_combo.currentData())
    if member_id is None or not build_name:
        page.status.warning(
            "The selected roster player needs at least one saved build before this chair can be assigned safely."
        )
        return

    try:
        if mode_combo.currentData() == "adopt":
            result = service.adopt_prescribed_setup(
                plan_name=plan.name,
                slot_name=slot.slot_name,
                member_id=int(member_id),
                base_build_name=build_name,
                new_build_name=new_name.text(),
            )
            action = f"created and assigned new build {new_name.text().strip()!r}"
        else:
            result = service.assign_existing_build(
                plan_name=plan.name,
                slot_name=slot.slot_name,
                member_id=int(member_id),
                build_name=build_name,
            )
            action = f"assigned existing build {build_name!r}"
    except (OSError, ValueError) as exc:
        page.status.error(str(exc))
        return

    # Refresh both the compatibility BuildRoster and the generated-team view.
    if hasattr(page, "build_service"):
        try:
            page.roster = page.build_service.load()
        except Exception:
            pass
    if hasattr(page, "_refresh_generated_plan_choices"):
        page._refresh_generated_plan_choices(result.name)
    page._populate_assignment_table()
    page.status.success(
        f"{slot.slot_name}: {action}. Original recruit prescription preserved for later encounter evaluation."
    )
    _update_assign_button(page)


def _init_with_recruit_adoption(self, parent=None) -> None:
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, parent)

    data_dir = get_data_dir()
    db = EsoDatabase(data_dir / "eso.db")
    self._roster_recruit_roster_service = RosterService(db)
    plans = getattr(self, "generated_plan_service", None) or GeneratedRosterPlanService(db)
    self._roster_recruit_adoption_service = RosterRecruitAdoptionService(
        builds=BuildService(data_dir / "builds.json"),
        plans=plans,
        roster=self._roster_recruit_roster_service,
    )

    self.assign_recruit_button = QPushButton("Assign Recruit")
    self.assign_recruit_button.setEnabled(False)
    self.assign_recruit_button.clicked.connect(lambda *_: _show_recruit_dialog(self))
    self.header.add_context_widget(self.assign_recruit_button)

    self.assignment_table.itemSelectionChanged.connect(
        lambda: _update_assign_button(self)
    )
    self.view_combo.currentTextChanged.connect(lambda *_: _update_assign_button(self))
    if hasattr(self, "generated_plan_combo"):
        self.generated_plan_combo.currentTextChanged.connect(
            lambda *_: _update_assign_button(self)
        )
    _update_assign_button(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_INIT
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    _ORIGINAL_INIT = RosterPage.__init__
    RosterPage.__init__ = _init_with_recruit_adoption
    _INSTALLED = True
