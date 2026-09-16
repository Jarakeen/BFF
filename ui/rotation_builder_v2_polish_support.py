from __future__ import annotations

"""Mockup polish plus live evidence surfacing for Rotation Builder V2.

This layer is deliberately presentation-oriented. It tightens the finished six-tab
workspace and exposes mechanics that are already canonical rather than inventing
planner semantics for controls that are still future work.
"""

from PySide6.QtWidgets import QLabel, QRadioButton, QTabWidget, QWidget

from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    discover_healer_heavy_attack_build_incentives,
)
from ui.components.foundry_card import FoundryCard


def _card(page, title: str) -> FoundryCard | None:
    wanted = str(title or "").strip().casefold()
    for card in page.findChildren(FoundryCard):
        if str(card.title_label.text() or "").strip().casefold() == wanted:
            return card
    return None


def _effective_build(page):
    resolver = getattr(page, "rotation_effective_build", None)
    if callable(resolver):
        return resolver()
    return page._selected_build()


def _format_incentive(item) -> str:
    bar = str(getattr(item, "bar", "") or "").strip().title() or "Unknown"
    name = str(getattr(item, "name", "") or "Heavy Attack").strip()
    kind = getattr(item, "kind", None)
    effect = str(getattr(item, "required_effect_name", "") or "").strip().replace("_", " ").title()
    duration = getattr(item, "effective_effect_duration_seconds", None)
    if duration is None:
        duration = getattr(item, "maximum_effect_duration_seconds", None)
    recurrence = getattr(item, "recurrence_seconds", None)
    upkeep = bool(getattr(item, "maintain_effect_uptime", False))

    if kind is HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT:
        reason = effect or name
        if upkeep and duration is not None:
            return f"{bar} bar • {name}: fully charged HA maintains {reason} ({float(duration):g}s effect)."
        if recurrence is not None:
            return f"{bar} bar • {name}: fully charged HA required; cadence evidence {float(recurrence):g}s."
        return f"{bar} bar • {name}: fully charged HA required for {reason}."
    if kind is HeavyAttackBuildIncentiveKind.RECOVERY_VALUE:
        return f"{bar} bar • {name}: fully charged HA is a verified recovery option."
    return f"{bar} bar • {name}: HA has build-aware healing value."


def _refresh_detected_build_evidence(page) -> None:
    label = getattr(page, "rotation_detected_build_requirements_label", None)
    proc_label = getattr(page, "rotation_proc_status_label", None)
    if label is None and proc_label is None:
        return

    build = _effective_build(page)
    if build is None:
        text = "Select a build to inspect live rotation requirements."
        if label is not None:
            label.setText(text)
        if proc_label is not None:
            proc_label.setText(text)
        return

    incentives = tuple(discover_healer_heavy_attack_build_incentives(build))
    required = tuple(
        item for item in incentives if item.kind is HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT
    )
    recovery = tuple(
        item for item in incentives if item.kind is HeavyAttackBuildIncentiveKind.RECOVERY_VALUE
    )

    if incentives:
        lines = ["Detected from the resolved build:"]
        lines.extend(f"• {_format_incentive(item)}" for item in incentives)
        text = "\n".join(lines)
    else:
        text = (
            "No reviewed Heavy Attack obligation or recovery incentive was detected from "
            "the resolved build. Ability priorities below remain live generation inputs."
        )

    if label is not None:
        label.setText(text)

    if proc_label is not None:
        proc_lines: list[str] = []
        if required:
            proc_lines.append("Required HA effects")
            proc_lines.extend(f"• {_format_incentive(item)}" for item in required)
        if recovery:
            if proc_lines:
                proc_lines.append("")
            proc_lines.append("Recovery opportunities")
            proc_lines.extend(f"• {_format_incentive(item)}" for item in recovery)
        proc_label.setText(
            "\n".join(proc_lines)
            if proc_lines
            else "No reviewed HA-driven set/passive cadence is active on this resolved build."
        )


def _polish_builder_cards(page) -> None:
    compact_titles = (
        "Rotation Style",
        "Execution Profile",
        "Sustain & Resources",
        "Generate & Results",
    )
    for title in compact_titles:
        card = _card(page, title)
        if card is not None:
            card.set_body_margins(10, 6, 10, 7)
            card.set_body_spacing(4)

    for control_name in (
        "rotation_la_reliability_combo",
        "rotation_bar_swap_comfort_combo",
        "rotation_heavy_behavior_combo",
        "rotation_complexity_combo",
        "rotation_primary_resource_combo",
        "rotation_minimum_reserve_spin",
        "potion_combo",
        "execute_spin",
        "target_type_combo",
    ):
        control = getattr(page, control_name, None)
        if control is not None:
            control.setMinimumHeight(30)
            control.setMaximumHeight(30)

    rules = _card(page, "Rotation Rules & Requirements")
    if rules is not None:
        rules.set_body_margins(8, 5, 8, 6)
        rules.set_body_spacing(4)

    pressure = _card(page, "Pressure Windows")
    if pressure is not None:
        pressure.set_body_margins(8, 5, 8, 6)
        pressure.set_body_spacing(4)


def _polish_rotation_style(page) -> None:
    group = getattr(page, "rotation_style_group", None)
    if group is None:
        return
    for button in group.buttons():
        if not isinstance(button, QRadioButton):
            continue
        title = str(button.text() or "").strip()
        supported = title == "Semi-static"
        button.setEnabled(supported)
        parent = button.parentWidget()
        if isinstance(parent, QWidget):
            parent.setMinimumHeight(70)
            parent.setMaximumHeight(82)
        if title == "Semi-static":
            button.setChecked(True)


def _install_detected_build_surface(page) -> None:
    tabs = getattr(page, "rotation_rule_tabs", None)
    if not isinstance(tabs, QTabWidget):
        tabs = getattr(page, "rotation_rules_tabs", None)
    if isinstance(tabs, QTabWidget) and tabs.count() > 0:
        detected = tabs.widget(0)
        layout = detected.layout() if detected is not None else None
        if layout is not None and not hasattr(page, "rotation_detected_build_requirements_label"):
            label = QLabel()
            label.setWordWrap(True)
            label.setProperty("rotationDetectedEvidence", True)
            label.setProperty("muted", True)
            page.rotation_detected_build_requirements_label = label
            layout.insertWidget(1, label)

    _refresh_detected_build_evidence(page)

    if bool(getattr(page, "_rotation_detected_build_refresh_installed", False)):
        return
    for control_name in (
        "character_combo",
        "build_combo",
        "rotation_team_combo",
        "rotation_boss_combo",
        "rotation_content_combo",
    ):
        control = getattr(page, control_name, None)
        signal = getattr(control, "currentIndexChanged", None) if control is not None else None
        if signal is not None:
            signal.connect(lambda *_args: _refresh_detected_build_evidence(page))
    page._rotation_detected_build_refresh_installed = True


def _polish_result_surface(page) -> None:
    summary = getattr(page, "rotation_v2_result_summary", None)
    if summary is not None:
        summary.setMinimumHeight(28)
        summary.setProperty("sidebarHeading", True)
    hint = getattr(page, "rotation_result_hint", None)
    if hint is not None:
        hint.setMaximumHeight(42)


def install_rotation_builder_v2_polish(page) -> None:
    """Apply the dense mockup proportions and surface already-real build evidence."""
    if bool(getattr(page, "_rotation_builder_v2_polish_installed", False)):
        return

    _polish_builder_cards(page)
    _polish_rotation_style(page)
    _install_detected_build_surface(page)
    _polish_result_surface(page)

    tabs = getattr(page, "rotation_builder_tabs", None)
    if tabs is not None:
        tabs.setDocumentMode(True)
        tabs.setMovable(False)
        tabs.setUsesScrollButtons(False)

    page._rotation_builder_v2_polish_installed = True


__all__ = ["install_rotation_builder_v2_polish"]
