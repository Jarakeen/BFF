from __future__ import annotations

"""Install explicit RaidPlan scope support on the existing Coverage page.

The Coverage page remains the owner of static capability auditing. This adapter only binds
one explicit RaidPlan to its exact saved builds and raid-lead assignment labels. It never
falls back to all saved builds when a plan chair cannot be resolved.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidgetItem

from models.raid_plan import RaidPlan
from services.raid_group_effect_catalog import (
    GROUP_COVERAGE_BY_NAME,
    GROUP_COVERAGE_NAMES,
)
from services.raid_plan_coverage_scope_service import RaidPlanCoverageScopeService
from services.raid_unique_support_set_catalog import (
    UNIQUE_SUPPORT_SET_BY_NAME,
    UNIQUE_SUPPORT_SET_NAMES,
)

_INSTALLED = False
_ORIGINAL_REFRESH = None

# Raid Plan scope must render the same raid-facing effect universe as ordinary Coverage,
# not only the older default-required profile. Unique-set references override duplicate
# generic rows so their terse type label and exact set semantics survive the handoff.
REFERENCE_BY_NAME = {**GROUP_COVERAGE_BY_NAME, **UNIQUE_SUPPORT_SET_BY_NAME}
RAID_PLAN_COVERAGE_NAMES = tuple(
    dict.fromkeys((*GROUP_COVERAGE_NAMES, *UNIQUE_SUPPORT_SET_NAMES))
)


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


def _render_raid_plan_scope(page) -> None:
    scope = getattr(page, "_raid_plan_coverage_scope", None)
    if scope is None:
        return

    snapshot = page.snapshot_for_builds(scope.resolved_builds)
    page.scope_card.set_title(f"Raid Plan: {scope.plan_name}")
    resolved = len(scope.members)
    unresolved = len(scope.unresolved)
    member_text = ", ".join(
        f"{row.seat_id}: {row.player_label} ({row.build.BuildName or 'Saved Build'})"
        for row in scope.members
    ) or "No selected saved builds resolved yet."
    unresolved_text = ""
    if scope.unresolved:
        unresolved_text = "\nUnresolved: " + " | ".join(scope.unresolved[:4])
        if len(scope.unresolved) > 4:
            unresolved_text += f" | +{len(scope.unresolved) - 4} more"
    page.scope_note.setText(
        f"{scope.named_members}/{scope.total_chairs} players named • "
        f"{resolved} selected build(s) resolved • {unresolved} unresolved chair(s)\n"
        f"{member_text}{unresolved_text}\n"
        "Raid Plan snapshot. Static build evidence is audited exactly as selected; "
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
                item.setToolTip("Static build evidence only. Uptime is not inferred.")
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
    global _INSTALLED, _ORIGINAL_REFRESH
    if _INSTALLED:
        return

    from ui.coverage_page import CoveragePage

    _ORIGINAL_REFRESH = CoveragePage.refresh

    def refresh_with_raid_plan(self) -> None:
        if (
            getattr(self, "scope_combo", None) is not None
            and self.scope_combo.currentData() == "raid_plan"
            and getattr(self, "_raid_plan_coverage_scope", None) is not None
        ):
            _render_raid_plan_scope(self)
            return
        _ORIGINAL_REFRESH(self)

    def set_raid_plan_scope(self, raid_plan: RaidPlan) -> None:
        if not isinstance(raid_plan, RaidPlan):
            raise TypeError("Coverage Raid Plan scope requires RaidPlan")
        try:
            roster = self.build_service.load()
            saved_builds = tuple(getattr(roster, "Members", ()) or ())
            scope = RaidPlanCoverageScopeService().compose(
                raid_plan=raid_plan,
                saved_builds=saved_builds,
                coverage_effect_names=_effect_names(self),
            )
        except Exception as exc:
            self.status.error(f"Could not build Raid Plan Coverage scope: {exc}")
            return

        self._raid_plan_coverage_scope = scope
        self.scope_combo.blockSignals(True)
        index = self.scope_combo.findData("raid_plan")
        if index < 0:
            self.scope_combo.addItem("Raid Plan", "raid_plan")
            index = self.scope_combo.findData("raid_plan")
        self.scope_combo.setItemText(index, f"Raid Plan: {raid_plan.name}")
        self.scope_combo.setCurrentIndex(index)
        self.scope_combo.blockSignals(False)
        self.tabs.setCurrentIndex(0)
        self.refresh()

    CoveragePage.refresh = refresh_with_raid_plan
    CoveragePage.set_raid_plan_scope = set_raid_plan_scope
    _INSTALLED = True


__all__ = ["install"]
