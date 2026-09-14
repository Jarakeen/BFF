from __future__ import annotations

"""Compose reviewed class-line mechanics into an Extreme Recovery route frontier.

This service is shared by Health, Magicka, and Stamina Recovery objectives. It
combines only mechanics already owned by canonical services: static passive
projection, reviewed active-bar slot allocations, legal class-line configurations,
and pure-class Class Mastery selections. Contextual passives that still need a
runtime witness remain explicit obligations and are never converted into zero or
free score.
"""

from dataclasses import dataclass
from pathlib import Path
import re

from services.extreme_class_configuration_service import ExtremeClassConfigurationService
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService
from services.extreme_passive_projection_service import (
    ExtremePassiveProjectionService,
    ExtremePassiveProjectionStatus,
)
from services.extreme_skill_universe_service import ExtremeSkillDomain, ExtremeSkillUniverseService
from services.extreme_subclass_slot_allocation_service import ExtremeSubclassSlotAllocationService

_SUPPORTED = {"health_recovery", "magicka_recovery", "stamina_recovery"}
# These passives are numerically owned by the active-bar slot-allocation service.
# They must not also be included through static tooltip projection, even when the
# projector can losslessly recognize the percentage clause.
_REVIEWED_SLOT_CONTEXT = {"flourish", "wellspring of the abyss"}


def _line_id(value: object) -> str:
    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _mentions_objective_recovery(text: str, objective_key: str) -> bool:
    value = " ".join(str(text or "").casefold().split())
    resource = objective_key.removesuffix("_recovery")
    if f"{resource} recovery" in value:
        return True
    if resource not in value or "recovery" not in value:
        return False
    resources = {name for name in ("health", "magicka", "stamina") if name in value}
    return resource in resources and len(resources) >= 2


@dataclass(frozen=True)
class ExtremeRecoveryClassRouteCandidate:
    objective_key: str
    base_class: str
    equipped_skill_lines: tuple[str, ...]
    is_pure_class: bool
    static_flat: float
    static_percent: float
    slot_projected_delta: float
    mastery_projected_delta: float
    projected_delta: float
    slot_counts: tuple[tuple[str, int], ...] = ()
    reviewed_sources: tuple[str, ...] = ()
    runtime_obligations: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeRecoveryClassRouteFrontier:
    objective_key: str
    reference_value: float
    candidates: tuple[ExtremeRecoveryClassRouteCandidate, ...]
    best_reviewed_candidate: ExtremeRecoveryClassRouteCandidate | None
    unresolved_runtime_obligations: tuple[str, ...]

    @property
    def route_denominator_closed(self) -> bool:
        return not self.unresolved_runtime_obligations


class ExtremeRecoveryClassRouteFrontierService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.passives = tuple(
            row
            for row in ExtremeSkillUniverseService(self.database_path).all_player_skills()
            if row.is_passive and row.domain is ExtremeSkillDomain.CLASS
        )
        self.mastery_pairs = ExtremeClassMasteryPairService(self.database_path)

    def _static_for_lines(
        self,
        equipped_skill_lines: tuple[str, ...],
        objective_key: str,
        reference_value: float,
    ) -> tuple[float, float, float, tuple[str, ...], tuple[str, ...]]:
        legal = {_line_id(line) for line in equipped_skill_lines}
        flat = 0.0
        percent = 0.0
        projected = 0.0
        sources: list[str] = []
        obligations: list[str] = []

        for passive in self.passives:
            if _line_id(passive.skill_line) not in legal:
                continue

            # Slot-scaled mechanics have one numeric owner. Skip them before
            # static projection so Flourish cannot be counted once from its
            # tooltip percentage and again from the active-bar slot witness.
            if passive.name.casefold() in _REVIEWED_SLOT_CONTEXT:
                continue

            projection = ExtremePassiveProjectionService.project(passive)
            relevant = tuple(
                row for row in projection.contributions if row.objective_key == objective_key
            )
            if relevant:
                for row in relevant:
                    flat += float(row.flat)
                    percent += float(row.percent_of_reference)
                    value = row.projected_delta(reference_value)
                    if value is None:
                        obligations.append(
                            f"{passive.skill_line}: {passive.name} requires Recovery reference value"
                        )
                        continue
                    projected += float(value)
                    sources.append(row.source or f"{passive.skill_line}: {passive.name}")
                continue

            if not _mentions_objective_recovery(passive.description, objective_key):
                continue
            if projection.status in {
                ExtremePassiveProjectionStatus.CONTEXT_REQUIRED,
                ExtremePassiveProjectionStatus.UNRESOLVED,
            }:
                obligations.append(f"{passive.skill_line}: {passive.name}")

        return (
            flat,
            percent,
            projected,
            tuple(dict.fromkeys(sources)),
            tuple(sorted(set(obligations), key=str.casefold)),
        )

    def frontier(
        self,
        objective_key: str,
        *,
        reference_value: float,
    ) -> ExtremeRecoveryClassRouteFrontier:
        objective = str(objective_key or "").strip().casefold()
        if objective not in _SUPPORTED:
            raise KeyError(f"unsupported Recovery objective: {objective_key!r}")
        reference = float(reference_value)
        if reference < 0:
            raise ValueError("reference_value must be non-negative")

        rows: list[ExtremeRecoveryClassRouteCandidate] = []
        all_obligations: set[str] = set()

        for config in ExtremeClassConfigurationService.all_candidates():
            static_flat, static_percent, static_delta, static_sources, obligations = (
                self._static_for_lines(config.equipped_skill_lines, objective, reference)
            )
            all_obligations.update(obligations)

            slot = ExtremeSubclassSlotAllocationService.best_allocation(
                config.equipped_skill_lines,
                objective,
                reference_value=reference,
            )
            slot_delta = float(slot.projected_delta) if slot is not None else 0.0
            slot_sources = slot.reviewed_sources if slot is not None else ()
            slot_counts = slot.slot_counts if slot is not None else ()

            mastery_delta = 0.0
            mastery_sources: tuple[str, ...] = ()
            if config.is_pure_class:
                mastery = self.mastery_pairs.best_for_class(
                    config.base_class,
                    objective,
                    reference_value=reference,
                )
                if mastery is not None and mastery.projected_delta is not None:
                    mastery_delta = float(mastery.projected_delta)
                    mastery_sources = tuple(
                        f"Class Mastery: {name}" for name in mastery.passive_names
                    )

            rows.append(
                ExtremeRecoveryClassRouteCandidate(
                    objective_key=objective,
                    base_class=config.base_class.value,
                    equipped_skill_lines=tuple(config.equipped_skill_lines),
                    is_pure_class=bool(config.is_pure_class),
                    static_flat=static_flat,
                    static_percent=static_percent,
                    slot_projected_delta=slot_delta,
                    mastery_projected_delta=mastery_delta,
                    projected_delta=static_delta + slot_delta + mastery_delta,
                    slot_counts=slot_counts,
                    reviewed_sources=tuple(
                        dict.fromkeys((*static_sources, *slot_sources, *mastery_sources))
                    ),
                    runtime_obligations=obligations,
                )
            )

        ordered = tuple(
            sorted(
                rows,
                key=lambda row: (
                    -row.projected_delta,
                    row.base_class,
                    row.equipped_skill_lines,
                    row.slot_counts,
                ),
            )
        )
        return ExtremeRecoveryClassRouteFrontier(
            objective_key=objective,
            reference_value=reference,
            candidates=ordered,
            best_reviewed_candidate=ordered[0] if ordered else None,
            unresolved_runtime_obligations=tuple(sorted(all_obligations, key=str.casefold)),
        )


__all__ = [
    "ExtremeRecoveryClassRouteCandidate",
    "ExtremeRecoveryClassRouteFrontier",
    "ExtremeRecoveryClassRouteFrontierService",
]
