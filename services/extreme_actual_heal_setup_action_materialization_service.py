from __future__ import annotations

"""Materialize reviewed H1 setup actions on a physically specified bar.

Temporary pre-event actions default to the inactive bar: cast, swap back, then
score the heal. Persistent slotted conditions may explicitly target the scored
active bar. Every placement consumes one of the five ordinary skill slots.

This layer performs placement only. Capability/route legality must already have
been proved by :mod:`extreme_actual_heal_setup_action_legality_service`.
"""

from dataclasses import dataclass

from models.build_model import BAR_SKILL_COUNT, PlayerBuild
from services.extreme_actual_heal_setup_action_legality_service import (
    ExtremeActualHealSetupActionWitness,
)


@dataclass(frozen=True)
class ExtremeActualHealSetupActionMaterialization:
    build: PlayerBuild
    setup_bar: str
    slot_index: int | None
    displaced_skill: str | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def materialized(self) -> bool:
        return self.slot_index is not None and not self.unresolved


class ExtremeActualHealSetupActionMaterializationService:
    """Place one proven non-Ultimate setup witness on the inactive H1 bar."""

    @staticmethod
    def _bar_attr(bar: str) -> str:
        return "BackBarSkills" if str(bar or "front").strip().casefold() == "back" else "FrontBarSkills"

    @classmethod
    def variants(
        cls,
        build: PlayerBuild,
        witness: ExtremeActualHealSetupActionWitness,
        *,
        active_bar: str = "front",
        placement_bar: str = "inactive",
    ) -> tuple[ExtremeActualHealSetupActionMaterialization, ...]:
        baseline = PlayerBuild.from_dict(build.to_dict())
        normalized_active = "back" if str(active_bar or "front").strip().casefold() == "back" else "front"
        placement = str(placement_bar or "inactive").strip().casefold()
        if placement not in {"active", "inactive"}:
            raise ValueError(f"unsupported H1 setup placement bar: {placement_bar!r}")
        setup_bar = (
            normalized_active
            if placement == "active"
            else ("front" if normalized_active == "back" else "back")
        )

        if not witness.proven or not str(witness.skill_name or "").strip():
            return (
                ExtremeActualHealSetupActionMaterialization(
                    build=baseline,
                    setup_bar=setup_bar,
                    slot_index=None,
                    unresolved=(
                        *tuple(witness.unresolved),
                        "H1 setup action cannot be materialized without a proven skill witness",
                    ),
                ),
            )

        active_attr = cls._bar_attr(normalized_active)
        setup_attr = cls._bar_attr(setup_bar)
        original_active = tuple(getattr(baseline, active_attr))
        original_setup = list(getattr(baseline, setup_attr))
        while len(original_setup) < BAR_SKILL_COUNT + 1:
            original_setup.append("")
        original_setup = original_setup[: BAR_SKILL_COUNT + 1]
        wanted_name = str(witness.skill_name).strip()
        wanted = wanted_name.casefold()

        existing = tuple(
            index
            for index, value in enumerate(original_setup[:BAR_SKILL_COUNT])
            if str(value or "").strip().casefold() == wanted
        )
        candidate_slots = existing
        if not candidate_slots:
            empties = tuple(
                index
                for index, value in enumerate(original_setup[:BAR_SKILL_COUNT])
                if not str(value or "").strip()
            )
            candidate_slots = empties if empties else tuple(range(BAR_SKILL_COUNT))

        results: list[ExtremeActualHealSetupActionMaterialization] = []
        for slot in candidate_slots:
            result = PlayerBuild.from_dict(baseline.to_dict())
            skills = list(getattr(result, setup_attr))
            while len(skills) < BAR_SKILL_COUNT + 1:
                skills.append("")
            skills = skills[: BAR_SKILL_COUNT + 1]
            current = str(skills[slot] or "").strip()
            displaced = None if current.casefold() == wanted or not current else current
            skills[slot] = wanted_name
            setattr(result, setup_attr, skills)

            if placement == "inactive" and tuple(getattr(result, active_attr)) != original_active:
                results.append(
                    ExtremeActualHealSetupActionMaterialization(
                        build=baseline,
                        setup_bar=setup_bar,
                        slot_index=None,
                        unresolved=("inactive-bar setup placement mutated the scored active bar",),
                    )
                )
                continue

            results.append(
                ExtremeActualHealSetupActionMaterialization(
                    build=result,
                    setup_bar=setup_bar,
                    slot_index=slot,
                    displaced_skill=displaced,
                )
            )

        return tuple(results)

    @classmethod
    def materialize(
        cls,
        build: PlayerBuild,
        witness: ExtremeActualHealSetupActionWitness,
        *,
        active_bar: str = "front",
        placement_bar: str = "inactive",
    ) -> ExtremeActualHealSetupActionMaterialization:
        variants = cls.variants(
            build,
            witness,
            active_bar=active_bar,
            placement_bar=placement_bar,
        )
        materialized = tuple(item for item in variants if item.materialized)
        if not materialized:
            return variants[0]
        return sorted(
            materialized,
            key=lambda item: (
                item.displaced_skill is not None,
                -(item.slot_index if item.slot_index is not None else -1),
            ),
        )[0]


__all__ = [
    "ExtremeActualHealSetupActionMaterialization",
    "ExtremeActualHealSetupActionMaterializationService",
]
