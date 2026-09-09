from __future__ import annotations

from pathlib import Path

from minmax.build_candidate import BuildCandidate
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.effect_relationship import ConditionContext
from minmax.named_combat_buffs import canonical_buff_name, effects_for_buff
from minmax.runtime_effect_eligibility import (
    RuntimeEffectState,
    evaluate_effect_variant_runtime_eligibility,
)
from minmax.runtime_event import RuntimeEvent
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_effect_stream import process_effect_variant_runtime_stream
from minmax.runtime_effect_window import partition_runtime_effect_windows
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

    @staticmethod
    def _triggered_buff_name(effect) -> str | None:
        if effect.layer is not EffectLayer.CAST:
            return None
        if effect.target_type is not SupportTargetType.SELF:
            return None
        if effect.trigger is None:
            return None
        if effect.duration is None or float(effect.duration) <= 0.0:
            return None
        canonical = canonical_buff_name(str(effect.name or "").replace("_", " "))
        if canonical is None or not effects_for_buff(canonical):
            return None
        return canonical

    def _triggered_available(self, build: PlayerBuild):
        result = []
        for ability_id, name in self.repository.available_skills(build.EsoClass):
            effects = tuple(
                effect
                for effect in self.repository.resolve(ability_id)
                if self._triggered_buff_name(effect) is not None
            )
            if effects:
                result.append((int(ability_id), str(name).strip(), effects))
        return tuple(result)

    def triggered_build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
        protected_entity_id: str,
        active_bar: str,
        event: RuntimeEvent,
        snapshot_time_seconds: float,
        state: RuntimeEffectState = RuntimeEffectState(),
        chance_roll: float | None = None,
        condition_context: ConditionContext | None = None,
    ) -> tuple[BuildCandidate, ...]:
        snapshot = float(snapshot_time_seconds)
        if snapshot < event.time_seconds:
            raise ValueError("triggered skill buff snapshot cannot precede the runtime event")
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
        elapsed = snapshot - event.time_seconds
        for ability_id, candidate_name, effects in self._triggered_available(baseline_build):
            active_buffs = []
            for effect in effects:
                eligibility = evaluate_effect_variant_runtime_eligibility(
                    event,
                    effect,
                    state=state,
                    chance_roll=chance_roll,
                    condition_context=condition_context,
                )
                buff = self._triggered_buff_name(effect)
                if (
                    eligibility.eligible
                    and buff is not None
                    and elapsed < float(effect.duration)
                ):
                    active_buffs.append(buff)
            active_buffs = list(dict.fromkeys(active_buffs))
            if not active_buffs:
                continue

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
                            f"actual-heal-triggered-skill-buff:{active_bar}:"
                            f"{slot_index}:{ability_id}:{event.trigger}"
                        ),
                        path=f"{attr}[{slot_index}]",
                        before=before,
                        after={
                            "skill": candidate_name,
                            "ability_id": ability_id,
                            "runtime_trigger": event.trigger,
                            "named_buffs": tuple(active_buffs),
                        },
                        source="extreme:actual-heal:triggered-skill-buff",
                    )
                )
        return tuple(result)

    def active_triggered_named_buffs(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
        event: RuntimeEvent,
        snapshot_time_seconds: float,
        state: RuntimeEffectState = RuntimeEffectState(),
        chance_roll: float | None = None,
        condition_context: ConditionContext | None = None,
    ) -> tuple[str, ...]:
        snapshot = float(snapshot_time_seconds)
        if snapshot < event.time_seconds:
            raise ValueError("triggered skill buff snapshot cannot precede the runtime event")
        elapsed = snapshot - event.time_seconds
        available = {name.casefold(): (ability_id, effects) for ability_id, name, effects in self._triggered_available(build)}
        attr = "BackBarSkills" if str(active_bar or "front").casefold() == "back" else "FrontBarSkills"
        result: list[str] = []
        for raw_name in list(getattr(build, attr))[:5]:
            name = str(raw_name or "").strip()
            resolved = available.get(name.casefold())
            if resolved is None:
                continue
            _, effects = resolved
            for effect in effects:
                eligibility = evaluate_effect_variant_runtime_eligibility(
                    event,
                    effect,
                    state=state,
                    chance_roll=chance_roll,
                    condition_context=condition_context,
                )
                buff = self._triggered_buff_name(effect)
                if (
                    eligibility.eligible
                    and buff is not None
                    and elapsed < float(effect.duration)
                ):
                    result.append(buff)
        return tuple(dict.fromkeys(result))

    def active_triggered_named_buffs_history(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
        attempts: tuple[RuntimeEffectEventAttempt, ...],
        snapshot_time_seconds: float,
    ) -> tuple[str, ...]:
        snapshot = float(snapshot_time_seconds)
        available = {name.casefold(): effects for _, name, effects in self._triggered_available(build)}
        attr = "BackBarSkills" if str(active_bar or "front").casefold() == "back" else "FrontBarSkills"
        result: list[str] = []
        for raw_name in list(getattr(build, attr))[:5]:
            effects = available.get(str(raw_name or "").strip().casefold())
            if not effects:
                continue
            for effect in effects:
                buff = self._triggered_buff_name(effect)
                if buff is None:
                    continue
                relevant = tuple(attempt for attempt in attempts if attempt.event.time_seconds <= snapshot)
                if not relevant:
                    continue
                stream = process_effect_variant_runtime_stream(relevant, effect)
                partition = partition_runtime_effect_windows(stream.final_state.windows, at_time_seconds=snapshot)
                if any(window.effect_name == effect.name for window in partition.active):
                    result.append(buff)
        return tuple(dict.fromkeys(result))

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
