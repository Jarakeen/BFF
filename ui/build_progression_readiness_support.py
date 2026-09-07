from __future__ import annotations

"""Surface rotation-cost progression readiness inside the Builds workspace.

This layer is deliberately read-only. Equipment may show which canonical armor
skill-line ownership matters for the current build's resource costs, but only the
existing Character Progression editor may persist character-owned progression.
"""

from PySide6.QtWidgets import QLabel

from minmax.resource_costs import ResourceType
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter
from services.rotation_progression_readiness_service import (
    RotationProgressionReadiness,
    RotationProgressionReadinessService,
)

_INSTALLED = False


def _readiness_text(result: RotationProgressionReadiness) -> str:
    resource = result.resource.value.title()
    if result.ready:
        return f"{resource} cost readiness: READY"
    if result.missing_cost_relevant_skill_lines:
        missing = ", ".join(result.missing_cost_relevant_skill_lines)
        return f"{resource} cost readiness: BLOCKED, missing canonical ownership: {missing}"
    if result.unresolved:
        return f"{resource} cost readiness: BLOCKED, canonical progression unresolved"
    return f"{resource} cost readiness: BLOCKED"


def _status_text(
    magicka: RotationProgressionReadiness,
    stamina: RotationProgressionReadiness,
) -> str:
    lines = [
        _readiness_text(magicka),
        _readiness_text(stamina),
    ]
    equipped = tuple(dict.fromkeys(magicka.equipped_armor_skill_lines + stamina.equipped_armor_skill_lines))
    if equipped:
        lines.append("Current build evidence: " + ", ".join(equipped) + " equipped")
    lines.append(
        "Equipment is evidence only. Save owned skill lines below to update canonical character progression for all builds."
    )
    return "\n".join(lines)


def _assess_for_page(page, build):
    catalog_service = page.build_service.canonical.catalog_service
    service = RotationProgressionReadinessService(
        MinmaxCharacterProgressionAdapter(catalog_service)
    )
    magicka = service.assess(build=build, resource=ResourceType.MAGICKA)
    stamina = service.assess(build=build, resource=ResourceType.STAMINA)
    return magicka, stamina


def _refresh_readiness(page, index: int | None = None) -> None:
    label = getattr(page, "progression_readiness_label", None)
    if label is None:
        return

    if index is None:
        index = getattr(page, "_progression_index", None)
    if index is None or index < 0 or index >= len(page.roster.Members):
        label.setText("Rotation cost readiness: select a character build.")
        return

    build = page.roster.Members[index]
    try:
        magicka, stamina = _assess_for_page(page, build)
    except Exception as exc:
        label.setText(f"Rotation cost readiness unavailable: {exc}")
        return

    label.setText(_status_text(magicka, stamina))


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage

    original_build_ui = BuildsPage._build_ui
    original_load_progression = BuildsPage._load_progression_tab
    original_save_progression = BuildsPage._save_progression_tab

    def build_ui_with_progression_readiness(self) -> None:
        original_build_ui(self)
        host = getattr(self, "progression_host", None)
        if host is None or host.parentWidget() is None:
            return
        layout = host.parentWidget().layout()
        if layout is None:
            return
        label = QLabel(
            "Rotation cost readiness: select a character build.",
            host.parentWidget(),
        )
        label.setWordWrap(True)
        label.setProperty("pageSubtitle", True)
        layout.insertWidget(1, label)
        self.progression_readiness_label = label

    def load_progression_with_readiness(self, index: int) -> None:
        original_load_progression(self, index)
        _refresh_readiness(self, index)

    def save_progression_with_readiness(self) -> None:
        original_save_progression(self)
        _refresh_readiness(self)

    BuildsPage._build_ui = build_ui_with_progression_readiness
    BuildsPage._load_progression_tab = load_progression_with_readiness
    BuildsPage._save_progression_tab = save_progression_with_readiness
    _INSTALLED = True
