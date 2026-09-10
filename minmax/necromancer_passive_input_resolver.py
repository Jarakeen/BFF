from __future__ import annotations

from dataclasses import replace
import re

from models.build_model import PlayerBuild

from .base_character_state import FlatContribution
from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs
from .skill_line_repository import SkillLineRepository


class NecromancerPassiveInputResolver:
    """Apply reviewed standing Necromancer passives to canonical build inputs.

    Live-U50 ``Last Gasp`` adds flat Max Health while Bone Tyrant belongs to the
    character's equipped class-line route. ``Health Avarice`` adds Healing
    Received for each Bone Tyrant ability slotted on the active bar. BFF stores
    received-side character modifiers in canonical ``healing_taken`` so every
    downstream healing consumer uses the same stat snapshot.

    Explicit ``PlayerBuild.ClassSkillLines`` are authoritative for subclass
    snapshots. A native Necromancer therefore owns all three native lines only
    when no explicit subclass route is supplied; foreign classes gain Bone
    Tyrant passive math only through an explicit Bone Tyrant route and proven
    passive ownership/rank.
    """

    GRAVE_LORD_ID = "grave_lord"
    BONE_TYRANT_ID = "bone_tyrant"
    LIVING_DEATH_ID = "living_death"
    NECROMANCER_LINE_IDS = frozenset(
        {GRAVE_LORD_ID, BONE_TYRANT_ID, LIVING_DEATH_ID}
    )

    LAST_GASP_MAX_HEALTH_BY_RANK = {
        1: 1206.0,
        2: 2412.0,
    }
    HEALTH_AVARICE_HEALING_TAKEN_PER_SLOT_BY_RANK = {
        1: 0.01,
        2: 0.03,
    }

    def __init__(self, skill_line_repository: SkillLineRepository) -> None:
        self.skill_line_repository = skill_line_repository

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def equipped_necromancer_line_ids(cls, build: PlayerBuild) -> frozenset[str]:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return frozenset(explicit) & cls.NECROMANCER_LINE_IDS
        if str(build.EsoClass or "").strip().casefold() == "necromancer":
            return cls.NECROMANCER_LINE_IDS
        return frozenset()

    @staticmethod
    def _active_skills(build: PlayerBuild, *, active_bar: str) -> tuple[str, ...]:
        skills = (
            build.BackBarSkills
            if str(active_bar or "front").casefold() == "back"
            else build.FrontBarSkills
        )
        return tuple(
            str(raw_name or "").strip()
            for raw_name in skills
            if str(raw_name or "").strip()
        )

    def _active_bone_tyrant_slot_count(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
    ) -> tuple[int, tuple[str, ...]]:
        count = 0
        unresolved_names: list[str] = []
        for name in self._active_skills(build, active_bar=active_bar):
            skill_line = self.skill_line_repository.skill_line_for_ability_name(name)
            if skill_line is None:
                unresolved_names.append(name)
                continue
            if self._line_id(skill_line) == self.BONE_TYRANT_ID:
                count += 1

        if not unresolved_names:
            return count, ()
        return count, (
            "Necromancer Health Avarice slot count is unresolved because the active-bar "
            "skill line could not be resolved for: " + ", ".join(unresolved_names),
        )

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
        last_gasp_rank: int | None = None,
        health_avarice_rank: int | None = None,
    ) -> GearCalculationInputs:
        equipped_lines = self.equipped_necromancer_line_ids(build)
        if self.BONE_TYRANT_ID not in equipped_lines:
            return result

        unresolved = list(result.unresolved)
        applied = result.applied_effect_count

        if last_gasp_rank is not None and int(last_gasp_rank) > 0:
            rank = int(last_gasp_rank)
            value = self.LAST_GASP_MAX_HEALTH_BY_RANK.get(rank)
            if value is None:
                unresolved.append(f"Unsupported Last Gasp rank: {rank}")
            else:
                source = FlatContribution("Necromancer: Last Gasp", value)
                result = replace(
                    result,
                    health=replace(
                        result.health,
                        skill_flat=result.health.skill_flat + value,
                        skill_flat_contributions=(
                            *result.health.skill_flat_contributions,
                            source,
                        ),
                    ),
                )
                applied += 1

        if health_avarice_rank is not None and int(health_avarice_rank) > 0:
            rank = int(health_avarice_rank)
            per_slot = self.HEALTH_AVARICE_HEALING_TAKEN_PER_SLOT_BY_RANK.get(rank)
            if per_slot is None:
                unresolved.append(f"Unsupported Health Avarice rank: {rank}")
            else:
                slots, slot_unresolved = self._active_bone_tyrant_slot_count(
                    build,
                    active_bar=active_bar,
                )
                unresolved.extend(slot_unresolved)
                if slots:
                    value = per_slot * slots
                    source = StatContribution("Necromancer: Health Avarice", value)
                    result = replace(
                        result,
                        core=replace(
                            result.core,
                            healing_taken=replace(
                                result.core.healing_taken,
                                additive_after_percent=(
                                    *result.core.healing_taken.additive_after_percent,
                                    source,
                                ),
                            ),
                        ),
                    )
                    applied += 1

        return replace(
            result,
            applied_effect_count=applied,
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
        )
