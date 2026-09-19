from __future__ import annotations

"""Install explicit RaidPlan scope support on the existing Coverage page.

The Coverage page remains the owner of static capability auditing. This adapter only binds
one explicit RaidPlan to its exact saved builds and raid-lead assignment labels. It never
falls back to all saved builds when a plan chair cannot be resolved.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidgetItem

from engine.config import DEFAULT_DATABASE, get_data_dir
from models.raid_plan import RaidPlan
from services.raid_group_effect_catalog import (
    GROUP_COVERAGE_BY_NAME,
    GROUP_COVERAGE_NAMES,
)
from services.raid_plan_coverage_assignment_service import (
    RaidPlanCoverageAssignmentService,
)
from services.raid_plan_coverage_scope_service import RaidPlanCoverageScopeService
from services.raid_plan_repository import RaidPlanRepository
from services.raid_unique_support_set_catalog import (
    UNIQUE_SUPPORT_SET_BY_NAME,
    UNIQUE_SUPPORT_SET_NAMES,
)
from services.raid_planned_gear_coverage_service import (
    PlannedGearCoverageProvider,
    RaidPlannedGearCoverageService,
)
from services.raid_planned_skill_coverage_service import (
    PlannedSkillCoverageProvider,
    RaidPlannedSkillCoverageService,
)

_INSTALLED = False
_ORIGINAL_REFRESH = None
_ORIGINAL_INIT = None

# Raid Plan scope must render the same raid-facing effect universe as ordinary Coverage,
# not only the older default-required profile. Unique-set references override duplicate
# generic rows so their terse type label and exact set semantics survive the handoff.
REFERENCE_BY_NAME = {**GROUP_COVERAGE_BY_NAME, **UNIQUE_SUPPORT_SET_BY_NAME}
RAID_PLAN_COVERAGE_NAMES = tuple(
    dict.fromkeys((*GROUP_COVERAGE_NAMES, *UNIQUE_SUPPORT_SET_NAMES))
)


def _plan_item_data(plan_id: object) -> str:
    return f"raid_plan:{str(plan_id or '').strip()}"


def _selected_plan_id(page) -> str:
    combo = getattr(page, "scope_combo", None)
    if combo is None:
        return ""
    data = str(combo.currentData() or "")
    return data.split(":", 1)[1] if data.startswith("raid_plan:") else ""


def _refresh_scope_plan_choices(page) -> None:
    """Coverage exposes saved Raid Plans only.

    Roster teams may seed plans elsewhere, and library-wide build audits remain useful
    internally, but neither is a valid user-facing Coverage scope in the Raid workflow.
    """
    combo = getattr(page, "scope_combo", None)
    if combo is None:
        return

    current_data = str(combo.currentData() or "")
    current_plan_id = (
        current_data.split(":", 1)[1]
        if current_data.startswith("raid_plan:")
        else ""
    )

    try:
        plans = RaidPlanRepository(get_data_dir() / "raid_plans.json").list_plans()
    except Exception:
        plans = ()

    combo.blockSignals(True)
    try:
        combo.clear()
        if not plans:
            combo.addItem("No saved Raid Plans", None)
            combo.setEnabled(False)
            return

        combo.setEnabled(True)
        selected_index = 0
        for plan in plans:
            trial = str(plan.trial_id or "").replace("-", " ").title()
            difficulty = str(plan.difficulty or "Difficulty not set")
            label = f"{plan.name} • {trial} • {difficulty}"
            combo.addItem(label, _plan_item_data(plan.plan_id))
            if current_plan_id and plan.plan_id.casefold() == current_plan_id.casefold():
                selected_index = combo.count() - 1
        combo.setCurrentIndex(selected_index)
    finally:
        combo.blockSignals(False)


def _load_selected_plan_scope(page):
    plan_id = _selected_plan_id(page)
    if not plan_id:
        return None

    plan = RaidPlanRepository(get_data_dir() / "raid_plans.json").get(plan_id)
    if plan is None:
        return None

    roster = page.build_service.load()
    saved_builds = tuple(getattr(roster, "Members", ()) or ())
    scope = RaidPlanCoverageScopeService().compose(
        raid_plan=plan,
        saved_builds=saved_builds,
        coverage_effect_names=_effect_names(page),
    )
    page._raid_plan_coverage_scope = scope
    return scope


def _effect_names(page) -> tuple[str, ...]:
    del page
    return RAID_PLAN_COVERAGE_NAMES


def _reference(effect: str):
    return REFERENCE_BY_NAME.get(effect)


def _required_text(effect: str) -> str:
    reference = _reference(effect)
    return "Yes" if reference is not None and reference.default_required else "No"


def _type_text(effect: str) -> str:
    reference = _reference(effect)
    if reference is None:
        return "Buff"
    return str(getattr(reference, "type_label", "") or reference.category)


def _apply_filters(page) -> None:
    if hasattr(page, "_apply_coverage_filters"):
        page._apply_coverage_filters()


def _overlay_planned_gear(snapshot, scope):
    """Share the canonical planned-gear evaluator with Comp Maker."""
    providers = tuple(
        PlannedGearCoverageProvider(
            seat_id=row.seat_id,
            provider_label=row.player_label,
            gear_sets=row.gear_sets,
        )
        for row in scope.planned_gear
    )
    return RaidPlannedGearCoverageService(DEFAULT_DATABASE).overlay(
        snapshot,
        providers,
        effect_names=RAID_PLAN_COVERAGE_NAMES,
    )

def _overlay_planned_skills(snapshot, scope):
    """Count explicit planned skills/class support as conditional planned coverage."""
    providers = tuple(
        PlannedSkillCoverageProvider(
            seat_id=row.seat_id,
            provider_label=row.player_label,
            eso_class=row.eso_class,
            skills=row.skills,
        )
        for row in scope.planned_skills
    )
    return RaidPlannedSkillCoverageService(DEFAULT_DATABASE).overlay(
        snapshot,
        providers,
        effect_names=RAID_PLAN_COVERAGE_NAMES,
    )

def _render_raid_plan_scope(page) -> None:
    scope = getattr(page, "_raid_plan_coverage_scope", None)
    if scope is None:
        return

    snapshot = page.snapshot_for_builds(scope.resolved_builds)
    snapshot = _overlay_planned_gear(snapshot, scope)
    snapshot = _overlay_planned_skills(snapshot, scope)
    page.scope_card.set_title(f"Raid Plan: {scope.plan_name}")
    resolved = len(scope.members)
    planned = len(scope.planned_gear)
    planned_skill_chairs = len(scope.planned_skills)
    unresolved = len(scope.unresolved)
    member_bits = [
        f"{row.seat_id}: {row.player_label} ({row.build.BuildName or 'Saved Build'})"
        for row in scope.members
    ]
    member_bits.extend(
        f"{row.seat_id}: {row.player_label} (planned {' + '.join(row.gear_sets)})"
        for row in scope.planned_gear
        if row.seat_id.casefold()
        not in {member.seat_id.casefold() for member in scope.members}
    )
    member_text = ", ".join(member_bits) or "No saved builds or planned gear resolved yet."
    unresolved_text = ""
    if scope.unresolved:
        unresolved_text = "\nUnresolved: " + " | ".join(scope.unresolved[:4])
        if len(scope.unresolved) > 4:
            unresolved_text += f" | +{len(scope.unresolved) - 4} more"
    page.scope_note.setText(
        f"{scope.named_members}/{scope.total_chairs} planned chair(s) • "
        f"{resolved} saved build(s) resolved • {planned} chair(s) with planned gear • "
        f"{planned_skill_chairs} chair(s) with planned skill/class evidence • "
        f"{unresolved} unresolved full-build chair(s)\n"
        f"{member_text}{unresolved_text}\n"
        "Raid Plan snapshot. Coverage answers whether the planned group has a source. "
        "Saved builds, planned gear, and explicit provider assignments can all count as "
        "Covered; Conditional/Planned labels describe proof strength, trigger requirements, "
        "or unresolved runtime evidence. Uptime is evaluated later."
    )

    page.table.setRowCount(0)
    assignment_service = RaidPlanCoverageAssignmentService()
    assignment_reviews = {}
    for effect in _effect_names(page):
        row = page.table.rowCount()
        page.table.insertRow(row)
        names = snapshot.providers.get(effect, [])
        conditional = snapshot.conditional_providers.get(effect, [])
        state = snapshot.status.get(effect, "unverified")
        review = assignment_service.review(
            effect_name=effect,
            scope=scope,
            snapshot=snapshot,
        )
        assignment_reviews[effect] = review
        planned_primary = tuple(
            (
                f"{provider} • {scope.source_note_for(effect, provider)}"
                if scope.source_note_for(effect, provider)
                else provider
            )
            for provider in review.primary
        )
        source_text = ", ".join(names) if names else (
            f"Conditional: {', '.join(conditional)}"
            if conditional
            else (
                "Planned: " + ", ".join(planned_primary)
                if planned_primary
                else "—"
            )
        )
        primary = ", ".join(review.primary) or "—"
        backup = ", ".join(review.backup) or "—"
        values = [
            effect,
            _type_text(effect),
            _required_text(effect),
            source_text,
            primary,
            backup,
            "—",
            "—",
            review.label,
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if column == 8:
                item.setData(Qt.ItemDataRole.UserRole, review.state)
                details = []
                if review.supported_primary:
                    details.append(
                        "Assigned provider confirmed by static evidence: "
                        + ", ".join(review.supported_primary)
                    )
                if review.conditional_primary:
                    details.append(
                        "Assigned provider has conditional evidence only: "
                        + ", ".join(review.conditional_primary)
                    )
                if review.unsupported_primary:
                    details.append(
                        "Assigned provider counts as planned coverage; exact static/runtime "
                        "source proof is unresolved: "
                        + ", ".join(review.unsupported_primary)
                    )
                if review.duplicate_primary:
                    details.append("More than one primary provider owns this effect.")
                item.setToolTip(
                    "\n".join(details)
                    or "No explicit primary provider is currently confirmed for this effect."
                )
            if column == 3:
                item.setData(Qt.ItemDataRole.UserRole, len(names) + len(conditional))
            if column in (4, 5):
                item.setToolTip(
                    "Explicit Raid Plan ownership. Coverage checks this provider against static/planned evidence before considering generic sources."
                )
            elif column >= 3 and column != 8:
                item.setToolTip(
                    "Saved-build static evidence plus reviewed planned-set evidence. "
                    "Planned gear is conditional because exact slotting/proc uptime is not inferred."
                )
            elif column == 2:
                item.setToolTip(
                    "Default raid coverage requirement."
                    if value == "Yes"
                    else "Reference-visible group effect; not a universal raid requirement."
                )
            else:
                item.setToolTip("Raid-facing coverage effect.")
            page.table.setItem(row, column, item)

    _apply_filters(page)
    visible_effects = _effect_names(page)
    available = sum(snapshot.status.get(name) == "available" for name in visible_effects)
    conditional_count = sum(snapshot.status.get(name) == "conditional" for name in visible_effects)
    not_found = sum(snapshot.status.get(name) == "not_found" for name in visible_effects)
    unverified = sum(snapshot.status.get(name, "unverified") == "unverified" for name in visible_effects)
    assigned_supported = sum(
        review.state == "assigned_supported" for review in assignment_reviews.values()
    )
    assigned_conditional = sum(
        review.state == "assigned_conditional" for review in assignment_reviews.values()
    )
    assigned_unproven = sum(
        review.state == "assigned_unproven" for review in assignment_reviews.values()
    )
    unassigned_sources = sum(
        review.state == "unassigned_available" for review in assignment_reviews.values()
    )
    backup_only = sum(
        review.state == "backup_only" for review in assignment_reviews.values()
    )
    planned_present = sum(
        review.counts_as_planned_coverage for review in assignment_reviews.values()
    )
    unassigned_gaps = sum(
        not review.counts_as_planned_coverage for review in assignment_reviews.values()
    )
    duplicate_primary = sum(
        review.duplicate_primary for review in assignment_reviews.values()
    )
    page.summary_card.clear()
    page.summary_card.addWidget(QLabel(
        f"TOTAL EFFECTS   {len(visible_effects)}\n"
        f"COVERED  {planned_present}\n"
        f"ASSIGNED + PROVEN  {assigned_supported}\n"
        f"ASSIGNED CONDITIONAL  {assigned_conditional}\n"
        f"ASSIGNED • RUNTIME UNPROVEN  {assigned_unproven}\n"
        f"COVERED / UNASSIGNED  {unassigned_sources}\n"
        f"BACKUP ONLY  {backup_only}\n"
        f"MISSING  {unassigned_gaps}\n"
        f"DUPLICATE PRIMARY  {duplicate_primary}\n"
        f"UNRESOLVED CHAIRS {unresolved}"
    ))
    page.providers_card.clear()
    provider_counts: dict[str, int] = {}
    conditional_counts: dict[str, int] = {}
    for effect in visible_effects:
        for name in snapshot.providers.get(effect, []):
            provider_counts[name] = provider_counts.get(name, 0) + 1
        for name in snapshot.conditional_providers.get(effect, []):
            conditional_counts[name] = conditional_counts.get(name, 0) + 1
    if provider_counts or conditional_counts:
        all_names = sorted(
            set(provider_counts) | set(conditional_counts),
            key=lambda name: (
                -(provider_counts.get(name, 0) + conditional_counts.get(name, 0)),
                name,
            ),
        )
        for name in all_names[:5]:
            static_count = provider_counts.get(name, 0)
            conditional_for_name = conditional_counts.get(name, 0)
            details = []
            if static_count:
                details.append(f"{static_count} static")
            if conditional_for_name:
                details.append(f"{conditional_for_name} conditional")
            page.providers_card.addWidget(QLabel(f"{name}   {', '.join(details)} effect(s) identified"))
    else:
        page.providers_card.addWidget(QLabel("No static or conditional sources identified."))

    attention = (
        assigned_unproven
        + unassigned_sources
        + backup_only
        + duplicate_primary
    )
    if unresolved or attention:
        page.status.warning(
            f"Raid Plan Coverage • {assigned_supported} assigned/proven • "
            f"{assigned_conditional} assigned/conditional • {unassigned_gaps} missing • "
            f"{attention} review item(s) • "
            f"{unresolved} unresolved chair(s)."
        )
    else:
        page.status.info(
            f"Raid Plan Coverage • {assigned_supported} assigned/proven • "
            f"{assigned_conditional} assigned/conditional • {planned_present} planned/present • "
            "runtime uptime remains unproven."
        )


def install() -> None:
    global _INSTALLED, _ORIGINAL_REFRESH, _ORIGINAL_INIT
    if _INSTALLED:
        return

    from ui.coverage_page import CoveragePage

    _ORIGINAL_INIT = CoveragePage.__init__
    _ORIGINAL_REFRESH = CoveragePage.refresh

    def init_with_raid_plan_picker(self, *args, **kwargs) -> None:
        _ORIGINAL_INIT(self, *args, **kwargs)
        _refresh_scope_plan_choices(self)

    def refresh_with_raid_plan(self, *args, **kwargs):
        _refresh_scope_plan_choices(self)
        data = str(self.scope_combo.currentData() or "")
        plan_id = _selected_plan_id(self)
        if plan_id:
            try:
                scope = _load_selected_plan_scope(self)
            except Exception as exc:
                self.status.error(f"Could not build Raid Plan Coverage scope: {exc}")
                return
            if scope is None:
                self.status.warning("Selected Raid Plan is no longer available.")
                return
            _render_raid_plan_scope(self)
            return

        self._raid_plan_coverage_scope = None
        self.table.setRowCount(0)
        self.scope_card.set_title("Choose a saved Raid Plan")
        self.scope_note.setText(
            "Coverage evaluates one saved trial plan at a time. "
            "Create or save a Raid Plan first, then return here."
        )
        self.summary_card.clear()
        self.summary_card.addWidget(QLabel("No Raid Plan selected."))
        self.providers_card.clear()
        self.providers_card.addWidget(QLabel("No plan-scoped provider evidence loaded."))
        self.status.info("Coverage is waiting for a saved Raid Plan.")
        return

    def set_raid_plan_scope(self, raid_plan: RaidPlan) -> None:
        """Compatibility helper: choose the plan in Coverage's own scope menu."""
        if not isinstance(raid_plan, RaidPlan):
            raise TypeError("Coverage Raid Plan scope requires RaidPlan")
        _refresh_scope_plan_choices(self)
        data = _plan_item_data(raid_plan.plan_id)
        index = self.scope_combo.findData(data)
        if index < 0:
            self.scope_combo.addItem(f"Raid Plan: {raid_plan.name}", data)
            index = self.scope_combo.findData(data)
        self.scope_combo.setCurrentIndex(index)
        self.tabs.setCurrentIndex(0)
        self.refresh()

    CoveragePage.__init__ = init_with_raid_plan_picker
    CoveragePage.refresh = refresh_with_raid_plan
    CoveragePage.set_raid_plan_scope = set_raid_plan_scope
    _INSTALLED = True


__all__ = ["install"]
