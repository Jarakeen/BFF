from __future__ import annotations

"""Targeted Rotation Builder V2 repairs that preserve canonical runtime ownership.

This module fixes two presentation/runtime seams without rebuilding the workspace:

* the already-canonical Duration / Uptime evidence card is placed directly in the
  Uptime & Resources grid instead of being wrapped in another FoundryCard; and
* V2 recovery-heavy stabilization reuses the reviewed saved-build weapon bridge so
  Heavy Attack restoration can resolve a real front/back weapon even when the broad
  CharacterBuild adapter cannot materialize a complete six-slot skill bar.

No ESO mechanic is reimplemented here. Heavy restoration remains owned by
RotationHeavySustainProjectionService and saved weapon identity remains owned by
RotationSavedBuildWeaponAttackEvaluationService.
"""

from dataclasses import replace
from types import MethodType

from PySide6.QtWidgets import QGridLayout

from minmax.resource_costs import ResourceType
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)
from services.rotation_saved_build_weapon_attack_evaluation_service import (
    RotationSavedBuildWeaponAttackEvaluationService,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from ui.components.foundry_card import FoundryCard
from ui.rotation_generation_support import RotationGenerationResult


def _tab(page, title: str):
    tabs = getattr(page, "rotation_builder_tabs", None)
    if tabs is None:
        return None
    wanted = str(title or "").strip().casefold()
    for index in range(tabs.count()):
        if str(tabs.tabText(index) or "").strip().casefold() == wanted:
            return tabs.widget(index)
    return None


def _card(page, title: str) -> FoundryCard | None:
    wanted = str(title or "").strip().casefold()
    for card in page.findChildren(FoundryCard):
        if str(card.title_label.text() or "").strip().casefold() == wanted:
            return card
    return None


def _flatten_duration_evidence(page) -> None:
    """Remove only the redundant outer Duration & Uptime Evidence card."""
    tab = _tab(page, "Uptime & Resources")
    inner = getattr(page, "duration_evidence_card", None)
    if tab is None or inner is None:
        return
    layout = tab.layout()
    if not isinstance(layout, QGridLayout):
        return

    outer = _card(page, "Duration & Uptime Evidence")
    if outer is None or outer is inner:
        return

    index = layout.indexOf(outer)
    if index < 0:
        return
    row, column, row_span, column_span = layout.getItemPosition(index)
    layout.takeAt(index)

    # Preserve the real evidence widget. Only the presentation wrapper is retired.
    inner.setParent(page)
    outer.setParent(None)
    outer.deleteLater()
    inner.set_body_margins(10, 7, 10, 8)
    inner.set_body_spacing(5)
    layout.addWidget(inner, row, column, row_span, column_span)


def _primary_resource(page, static_context, initial_bar: str) -> ResourceType:
    selected = str(page.rotation_primary_resource_combo.currentText() or "").strip()
    if selected == "Magicka":
        return ResourceType.MAGICKA
    if selected == "Stamina":
        return ResourceType.STAMINA
    magicka = static_context.maximum_amount_for(initial_bar, ResourceType.MAGICKA)
    stamina = static_context.maximum_amount_for(initial_bar, ResourceType.STAMINA)
    return ResourceType.MAGICKA if magicka >= stamina else ResourceType.STAMINA


def _install_saved_weapon_heavy_bridge(page) -> None:
    """Supersede the V2 recovery-heavy UI wrapper with saved-weapon bar evidence.

    The older V2 wrapper passed the broad SavedBuildCharacterAdapter result directly
    into Heavy Attack restoration. That adapter intentionally returns ``bar=None``
    whenever a complete canonical six-slot skill bar cannot be proven, even when the
    saved weapon itself is perfectly known. Heavy restoration only needs the weapon
    bar, so use the existing weapon-attack bridge that was built for exactly this
    separation of concerns.
    """
    generation = page.rotation_generation
    if bool(getattr(generation, "_rotation_v2_saved_weapon_heavy_bridge_installed", False)):
        return

    legacy_generate = generation.generate_with_evidence
    static_service = RotationStaticBuildContextService()
    heavy_service = RotationHeavySustainProjectionService(
        progression_adapter=static_service.progression_adapter
    )
    weapon_service = RotationSavedBuildWeaponAttackEvaluationService()

    def generate_without_legacy_recovery(*, build, request):
        """Call the already-wired V2 generator while bypassing its old recovery wrapper."""
        combo = page.rotation_heavy_behavior_combo
        previous = str(combo.currentText() or "")
        combo.blockSignals(True)
        combo.setCurrentText("Required only")
        try:
            return legacy_generate(build=build, request=request)
        finally:
            combo.setCurrentText(previous)
            combo.blockSignals(False)

    def generate_with_saved_weapon_heavies(_service, *, build, request):
        page._rotation_v2_last_recovery_projection = None
        behavior = str(page.rotation_heavy_behavior_combo.currentText() or "").strip()
        if behavior not in {"Use when needed", "Prefer safe windows"}:
            return legacy_generate(build=build, request=request)

        front_skills = tuple(getattr(build, "FrontBarSkills", ()) or ())[:5]
        initial_bar = (
            "front"
            if any(str(skill or "").strip() for skill in front_skills)
            else "back"
        )
        static_context = static_service.resolve(build)
        if not static_context.contexts:
            raise ValueError(
                "sustain Heavy Attacks require a resolved canonical static build context"
            )

        resource = _primary_resource(page, static_context, initial_bar)
        maximum_amount = static_context.maximum_amount_for(initial_bar, resource)
        trigger_fraction = float(page.rotation_minimum_reserve_spin.value()) / 100.0
        if maximum_amount <= 0:
            raise ValueError("sustain Heavy Attacks require a positive resource maximum")

        weapon_resolution = weapon_service.resolve(
            player_build=build,
            static_context=static_context,
        )
        character_build = weapon_resolution.build
        if character_build is None:
            detail = "; ".join(weapon_resolution.unresolved) or (
                "saved weapon bars could not be materialized"
            )
            raise ValueError("sustain Heavy Attacks unavailable: " + detail)

        generated_results: list[RotationGenerationResult] = []

        def generate(pressure_resolver):
            iteration_request = replace(
                request,
                stabilize_recovery_heavies=False,
                recovery_pressure_resolver=pressure_resolver,
            )
            result = generate_without_legacy_recovery(
                build=build,
                request=iteration_request,
            )
            generated_results.append(result)
            return result.plan

        def restoration_factory(plan):
            completion = heavy_service.completion_evidence_from_verified_reservations(plan)
            return heavy_service.restoration_resolver_for_plan(
                character_build=character_build,
                sustain_build=build,
                plan=plan,
                resource=resource,
                initial_bar=initial_bar,
                completion_evidence=completion,
            )

        stabilization = generation.recovery_stabilization.stabilize(
            build=build,
            generate=generate,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver_factory=restoration_factory,
            max_iterations=6,
            calculation_context=static_context.context_for(initial_bar),
            maximum_event_resolver=(
                lambda plan, tracked_resource: static_context.maximum_events_for(
                    plan,
                    tracked_resource,
                    initial_bar=initial_bar,
                )
            ),
            displayed_recovery_resolver_factory=(
                lambda plan, tracked_resource: static_context.displayed_recovery_resolver_for(
                    plan,
                    tracked_resource,
                    initial_bar=initial_bar,
                )
            ),
        )
        if not generated_results:
            raise RuntimeError("sustain Heavy Attack stabilization produced no generation pass")

        final_generated = generated_results[-1]
        page._rotation_v2_last_recovery_projection = stabilization.replay.final_projection
        page._rotation_v2_last_recovery_resource = resource
        return RotationGenerationResult(
            plan=stabilization.plan,
            duration_evidence=final_generated.duration_evidence,
            ultimate_projection=final_generated.ultimate_projection,
            recovery_stabilization=stabilization,
        )

    generation.generate_with_evidence = MethodType(
        generate_with_saved_weapon_heavies,
        generation,
    )
    generation._rotation_v2_saved_weapon_heavy_bridge_installed = True


def install_rotation_builder_v2_runtime_repairs(page) -> None:
    """Install narrow V2 repairs after the normal V2 finish/compact passes."""
    if bool(getattr(page, "_rotation_builder_v2_runtime_repairs_installed", False)):
        return
    _flatten_duration_evidence(page)
    _install_saved_weapon_heavy_bridge(page)
    page._rotation_builder_v2_runtime_repairs_installed = True


__all__ = ["install_rotation_builder_v2_runtime_repairs"]
