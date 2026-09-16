from __future__ import annotations

"""Materialize reviewed H1 setup actions on the inactive bar.

The scored heal stays on ``active_bar``.  A proven setup-action witness is placed on
the opposite bar, cast before the scored event, then H1 swaps back to the original
active bar.  This prevents a setup witness from inventing a sixth ordinary skill
slot or displacing the candidate heal being evaluated.

This layer performs placement only.  Capability/route legality must already have
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
    def materialize(
        cls,
        build: PlayerBuild,
        witness: ExtremeActualHealSetupActionWitness,
        *,
        active_bar: str = "front",
    ) -> ExtremeActualHealSetupActionMaterialization:
        result = PlayerBuild.from_dict(build.to_dict())
        normalized_active = "back" if str(active_bar or "front").strip().casefold() == "back" else "front"
        setup_bar = "front" if normalized_active == "back" else "back"

        if not witness.proven or not str(witness.skill_name or "").strip():
            return ExtremeActualHealSetupActionMaterialization(
                build=result,
                setup_bar=setup_bar,
                slot_index=None,
                unresolved=(
                    *tuple(witness.unresolved),
                    "H1 setup action cannot be materialized without a proven skill witness",
                ),
            )

        active_attr = cls._bar_attr(normalized_active)
        setup_attr = cls._bar_attr(setup_bar)
        original_active = tuple(getattr(result, active_attr))
        skills = list(getattr(result, setup_attr))
        while len(skills) < BAR_SKILL_COUNT + 1:
            skills.append("")
        skills = skills[: BAR_SKILL_COUNT + 1]

        wanted = str(witness.skill_name).strip().casefold()
        existing = next(
            (
                index
                for index, value in enumerate(skills[:BAR_SKILL_COUNT])
                if str(value or "").strip().casefold() == wanted
            ),
            None,
        )
        if existing is not None:
            slot = existing
            displaced = None
        else:
            empty = next(
                (
                    index
                    for index, value in enumerate(skills[:BAR_SKILL_COUNT])
                    if not str(value or "").strip()
                ),
                None,
            )
            slot = empty if empty is not None else BAR_SKILL_COUNT - 1
            displaced = str(skills[slot] or "").strip() or None
            skills[slot] = str(witness.skill_name).strip()

        setattr(result, setup_attr, skills)
        if tuple(getattr(result, active_attr)) != original_active:
            return ExtremeActualHealSetupActionMaterialization(
                build=PlayerBuild.from_dict(build.to_dict()),
                setup_bar=setup_bar,
                slot_index=None,
                unresolved=("inactive-bar setup placement mutated the scored active bar",),
            )

        return ExtremeActualHealSetupActionMaterialization(
            build=result,
            setup_bar=setup_bar,
            slot_index=slot,
            displaced_skill=displaced,
        )


__all__ = [
    "ExtremeActualHealSetupActionMaterialization",
    "ExtremeActualHealSetupActionMaterializationService",
]
