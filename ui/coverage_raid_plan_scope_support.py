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
from services.nonability_effect_provider_reference_service import (
    NonAbilityEffectProviderReferenceService,
    canonical_identity,
)
from services.raid_group_effect_catalog import (
    GROUP_COVERAGE_BY_NAME,
    GROUP_COVERAGE_NAMES,
)
from services.raid_plan_coverage_scope_service import RaidPlanCoverageScopeService
from services.raid_plan_repository import RaidPlanRepository
from services.raid_unique_support_set_catalog import (
    UNIQUE_SUPPORT_SET_BY_NAME,
    UNIQUE_SUPPORT_SET_NAMES,
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
    combo = getattr(page, "scope_combo", None)
    if combo is None:
        return

    current_data = combo.currentData()
    combo.blockSignals(True)
    try:
        for index in range(combo.count() - 1, -1, -1):
            if str(combo.itemData(index) or "").startswith("raid_plan:"):
                combo.removeItem(index)

        try:
            plans = RaidPlanRepository(get_data_dir() / "raid_plans.json").list_plans()
        except Exception:
            plans = ()

        for plan in plans:
            combo.addItem(f"Raid Plan: {plan.name}", _plan_item_data(plan.plan_id))

        if current_data is not None:
            target = combo.findData(current_data)
            if target >= 0:
                combo.setCurrentIndex(target)
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


def _planned_gear_provider_label(row, set_name: str) -> str:
    return f"{row.player_label} [planned: {set_name}]"


def _overlay_planned_gear(snapshot, scope):
    """Project only reviewed set relationships from Raid Plan planned gear.

    Planned sets prove raid-lead intent, not exact slotting, piece counts, bar state,
    proc activation, or uptime. All planned-set evidence is therefore Conditional.
    """
    status = dict(snapshot.status)
    providers = {name: list(values) for name, values in snapshot.providers.items()}
    conditional = {
        name: list(values)
        for name, values in snapshot.conditional_providers.items()
    }

    display_by_effect_key = {
        canonical_identity(name): name
        for name in RAID_PLAN_COVERAGE_NAMES
    }
    reviewed_rows = NonAbilityEffectProviderReferenceService(DEFAULT_DATABASE).gear()
    reviewed_by_set: dict[str, list[object]] = {}
    for item in reviewed_rows:
        reviewed_by_set.setdefault(item.source_name.casefold(), []).append(item)

    unique_by_set = {
        name.casefold(): reference
        for name, reference in UNIQUE_SUPPORT_SET_BY_NAME.items()
    }

    for row in scope.planned_gear:
        for set_name in row.gear_sets:
            key = str(set_name or "").strip().casefold()
            if not key:
                continue
            label = _planned_gear_provider_label(row, set_name)

            unique = unique_by_set.get(key)
            if unique is not None:
                effect_name = unique.name
                status.setdefault(effect_name, "unverified")
                providers.setdefault(effect_name, [])
                conditional.setdefault(effect_name, [])
                if label not in conditional[effect_name]:
                    conditional[effect_name].append(label)

            for reference in reviewed_by_set.get(key, ()):
                effect_name = display_by_effect_key.get(reference.effect_key)
                if effect_name is None:
                    continue
                status.setdefault(effect_name, "unverified")
                providers.setdefault(effect_name, [])
                conditional.setdefault(effect_name, [])
                if label not in conditional[effect_name]:
                    conditional[effect_name].append(label)

    for name in tuple(status):
        if providers.get(name):
            status[name] = "available"
        elif conditional.get(name):
            status[name] = "conditional"

    return type(snapshot)(status, providers, conditional)


def _render_raid_plan_scope(page) -> None:
    scope = getattr(page, "_raid_plan_coverage_scope", None)
    if scope is None:
        return

    snapshot = page.snapshot_for_builds(scope.resolved_builds)
    snapshot = _overlay_planned_gear(snapshot, scope)
    page.scope_card.set_title(f"Raid Plan: {scope.plan_name}")
    resolved = len(scope.members)
    planned = len(scope.planned_gear)
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
        f"{unresolved} unresolved full-build chair(s)\n"
        f"{member_text}{unresolved_text}\n"
        "Raid Plan snapshot. Saved builds use full static capability evidence; planned "
        "sets contribute reviewed set-only capability as Conditional evidence. "
        "Primary/Secondary labels show planning intent only and do not prove uptime."
    )

    page.table.setRowCount(0)
    for effect in _effect_names(page):
        row = page.table.rowCount()
        page.table.insertRow(row)
        names = snapshot.providers.get(effect, [])
        conditional = snapshot.conditional_providers.get(effect, [])
        state = snapshot.status.get(effect, "unverified")
        source_text = ", ".join(names) if names else (
            f"Conditional: {', '.join(conditional)}" if conditional else "—"
        )
        primary = ", ".join(scope.primary_for(effect)) or "—"
        backup = ", ".join(scope.secondary_for(effect)) or "—"
        values = [
            effect,
            _type_text(effect),
            _required_text(effect),
            source_text,
            primary,
            backup,
            "—",
            "—",
            {
                "available": "Available (static)",
                "conditional": "Conditional",
                "not_found": "Not identified",
                "unverified": "Unverified",
            }.get(state, "Unverified"),
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if column == 8:
                item.setData(Qt.ItemDataRole.UserRole, state)
            if column == 3:
                item.setData(Qt.ItemDataRole.UserRole, len(names) + len(conditional))
            if column in (4, 5):
                item.setToolTip(
                    "Explicit Raid Plan assignment label. This is planning intent, not proof that the effect is available or maintained."
                )
            elif column >= 3:
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
    page.summary_card.clear()
    page.summary_card.addWidget(QLabel(
        f"TOTAL EFFECTS   {len(visible_effects)}\n"
        f"STATIC SOURCES  {available}\n"
        f"CONDITIONAL     {conditional_count}\n"
        f"NOT IDENTIFIED  {not_found}\n"
        f"UNVERIFIED      {unverified}\n"
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

    if unresolved:
        page.status.warning(
            f"Raid Plan Coverage • {available} static + {conditional_count} conditional "
            f"of {len(visible_effects)} effects; {unresolved} chair(s) unresolved."
        )
    else:
        page.status.info(
            f"Raid Plan Coverage • {available} static + {conditional_count} conditional "
            f"of {len(visible_effects)} effects; uptime unknown."
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

    def refresh_with_raid_plan(self) -> None:
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

        if data.startswith("roster_team:"):
            from ui.coverage_health_check_support import run_team_health_check

            run_team_health_check(
                self,
                data.split(":", 1)[1],
                use_context=False,
            )
            return

        self._raid_plan_coverage_scope = None
        _ORIGINAL_REFRESH(self)

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
