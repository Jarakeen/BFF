from __future__ import annotations

from pathlib import Path

from minmax.build_candidate import BuildCandidate
from minmax.character_build.effect_layer import EffectLayer
from minmax.named_combat_buffs import canonical_buff_name, effects_for_buff
from minmax.skill_coefficient_repository import ability_entity_id
from minmax.skill_effect_repository import SkillEffectRepository
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService


class ExtremeActualHealSkillBuffCandidateService:
    """Discover legal self-buff skill carriers for an explicit pre-cast snapshot.

    Only unconditional SELF-target CAST effects with a positive sourced duration
    and a named stat-buff mapping are admitted. Triggered/conditional variants
    stay out of this first discovery slice rather than being optimistically
    treated as available.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        repository: SkillEffectRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.repository = repository or SkillEffectRepository(self.database_path)

    @staticmethod
    def _buff_name(effect) -> str | None:
        if effect.layer is not EffectLayer.CAST:
            return None
        if effect.target_type is not SupportTargetType.SELF:
            return None
        if effect.condition is not None or effect.trigger is not None:
            return None
        if effect.duration is None or float(effect.duration) <= 0.0:
            return None
        canonical = canonical_buff_name(str(effect.name or "").replace("_", " "))
        if canonical is None or not effects_for_buff(canonical):
            return None
        return canonical

    def _available(self, build: PlayerBuild):
        result = []
        for ability_id, name in self.repository.available_skills(build.EsoClass):
            buffs = tuple(
                dict.fromkeys(
                    buff
                    for effect in self.repository.resolve(ability_id)
                    if (buff := self._buff_name(effect))
                )
            )
            if buffs:
                result.append((int(ability_id), str(name).strip(), buffs))
        return tuple(result)

    def active_named_buffs(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
        elapsed_seconds: float,
    ) -> tuple[str, ...]:
        elapsed = float(elapsed_seconds)
        if elapsed < 0.0:
            raise ValueError("skill pre-cast elapsed time cannot be negative")
        available = {name.casefold(): ability_id for ability_id, name, _ in self._available(build)}
        attr = "BackBarSkills" if str(active_bar or "front").casefold() == "back" else "FrontBarSkills"
        seen: set[str] = set()
        buffs: list[str] = []
        for raw_name in list(getattr(build, attr))[:5]:
            name = str(raw_name or "").strip()
            ability_id = available.get(name.casefold())
            if ability_id is None:
                continue
            for effect in self.repository.resolve(ability_id):
                buff = self._buff_name(effect)
                if buff is None or elapsed >= float(effect.duration):
                    continue
                key = buff.casefold()
                if key in seen:
                    continue
                seen.add(key)
                buffs.append(buff)
        return tuple(buffs)

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
        protected_entity_id: str,
        active_bar: str,
    ) -> tuple[BuildCandidate, ...]:
        entity = str(protected_entity_id or "").strip()
        if not entity:
            return ()
        attr = "BackBarSkills" if str(active_bar or "front").casefold() == "back" else "FrontBarSkills"
        original = list(getattr(baseline_build, attr))
        while len(original) < 6:
            original.append("")
        original = original[:6]
        protected = {
            index
            for index, raw_name in enumerate(original[:5])
            if ability_entity_id(str(raw_name or "").strip()) == entity
        }
        if not protected:
            return ()

        result: list[BuildCandidate] = []
        for ability_id, candidate_name, buffs in self._available(baseline_build):
            for slot_index in range(5):
                if slot_index in protected:
                    continue
                before = str(original[slot_index] or "").strip()
                if before.casefold() == candidate_name.casefold():
                    continue
                if any(
                    index != slot_index
                    and str(name or "").strip().casefold() == candidate_name.casefold()
                    for index, name in enumerate(original[:5])
                ):
                    continue
                build = PlayerBuild.from_dict(baseline_build.to_dict())
                skills = list(getattr(build, attr))
                while len(skills) < 6:
                    skills.append("")
                skills = skills[:6]
                skills[slot_index] = candidate_name
                setattr(build, attr, skills)
                result.append(
                    ExtremeCompleteOptimizationService._direct_candidate(
                        build,
                        character_id=character_id,
                        baseline_build_id=baseline_build_id,
                        token=(
                            f"actual-heal-skill-buff:{active_bar}:"
                            f"{slot_index}:{ability_id}"
                        ),
                        path=f"{attr}[{slot_index}]",
                        before=before,
                        after={
                            "skill": candidate_name,
                            "ability_id": ability_id,
                            "named_buffs": buffs,
                        },
                        source="extreme:actual-heal:skill-buff",
                    )
                )
        return tuple(result)
