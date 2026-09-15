from __future__ import annotations

"""Project triggered self skill effects through the shared runtime engine.

This service is role-neutral. It reuses canonical SkillEffectRepository rows and the
Phase 7 ordered runtime stream, then separates named combat buffs from other timed
EffectVariants. It owns no objective scoring and invents no skill semantics.

When bar-tagged attempts are available, trigger eligibility is evaluated against the
skill bar that was active when each attempt occurred. This prevents a persistent
back-bar-triggered effect from disappearing merely because the snapshot itself is
later evaluated on the front bar. Untagged attempts remain a compatibility fallback
for older callers that do not carry bar provenance.

Mixed tagged + untagged history is never silently normalized. Tagged attempts remain
usable as proven evidence, while every untagged attempt is surfaced as unresolved
because its bar-local skill legality cannot be reconstructed honestly.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.named_combat_buffs import canonical_buff_name, effects_for_buff
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_effect_stream import process_effect_variant_runtime_stream
from minmax.runtime_effect_window import partition_runtime_effect_windows
from minmax.skill_effect_repository import SkillEffectRepository
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt


@dataclass(frozen=True)
class ExtremeSkillRuntimeEffectResult:
    active_buffs: tuple[str, ...] = ()
    active_effects: tuple[EffectVariant, ...] = ()
    unresolved: tuple[str, ...] = ()


class ExtremeSkillRuntimeEffectService:
    """Resolve active triggered self skill effects at one exact snapshot."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        repository: SkillEffectRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.repository = repository or SkillEffectRepository(self.database_path)

    @staticmethod
    def _is_runtime_candidate(effect: EffectVariant) -> bool:
        return bool(
            effect.layer is EffectLayer.CAST
            and effect.target_type is SupportTargetType.SELF
            and effect.trigger is not None
            and effect.duration is not None
            and float(effect.duration) > 0.0
        )

    @staticmethod
    def _named_buff(effect: EffectVariant) -> str | None:
        canonical = canonical_buff_name(str(effect.name or "").replace("_", " "))
        if canonical is None or not effects_for_buff(canonical):
            return None
        return canonical

    @staticmethod
    def _skills_for_bar(build: PlayerBuild, bar: str) -> set[str]:
        attr = "BackBarSkills" if bar == "back" else "FrontBarSkills"
        return {
            str(value or "").strip().casefold()
            for value in list(getattr(build, attr))[:5]
            if str(value or "").strip()
        }

    def resolve_history(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
        attempts: tuple[RuntimeEffectEventAttempt, ...],
        snapshot_time_seconds: float,
        bar_attempts: tuple[ExtremeRuntimeBarEffectAttempt, ...] = (),
    ) -> ExtremeSkillRuntimeEffectResult:
        snapshot = float(snapshot_time_seconds)
        snapshot_bar = (
            "back"
            if str(active_bar or "front").strip().casefold() == "back"
            else "front"
        )
        front_skills = self._skills_for_bar(build, "front")
        back_skills = self._skills_for_bar(build, "back")
        all_slotted = front_skills | back_skills
        if not all_slotted or (not attempts and not bar_attempts):
            return ExtremeSkillRuntimeEffectResult()

        available = {
            str(name or "").strip().casefold(): int(ability_id)
            for ability_id, name in self.repository.available_skills(build.EsoClass)
        }
        active_buffs: list[str] = []
        active_effects: list[EffectVariant] = []
        unresolved: list[str] = []

        legacy_attempts = tuple(
            attempt
            for attempt in attempts
            if float(attempt.event.time_seconds) <= snapshot + 1e-12
        )
        tagged_attempts = tuple(
            row
            for row in bar_attempts
            if float(row.attempt.event.time_seconds) <= snapshot + 1e-12
        )
        if tagged_attempts and legacy_attempts:
            unresolved.append(
                "Skill runtime history mixes bar-tagged and untagged effect attempts; "
                "untagged attempts cannot prove bar-local skill activation"
            )

        for skill_name in sorted(all_slotted):
            ability_id = available.get(skill_name)
            if ability_id is None:
                continue
            skill_bars = {
                bar
                for bar, slotted in (("front", front_skills), ("back", back_skills))
                if skill_name in slotted
            }
            for effect in self.repository.resolve(ability_id):
                if not self._is_runtime_candidate(effect):
                    continue

                if tagged_attempts:
                    relevant_attempts = tuple(
                        row.attempt
                        for row in tagged_attempts
                        if row.active_bar in skill_bars
                    )
                else:
                    # Compatibility path: without historical bar provenance, only
                    # the snapshot-active bar can honestly prove the skill was slotted.
                    if snapshot_bar not in skill_bars:
                        continue
                    relevant_attempts = legacy_attempts

                if not relevant_attempts:
                    continue
                stream = process_effect_variant_runtime_stream(relevant_attempts, effect)
                for step in stream.unresolved_steps:
                    reasons = (
                        step.transition.unresolved
                        or step.transition.activation.eligibility.reasons
                    )
                    if reasons:
                        unresolved.append(
                            f"{skill_name} {effect.name} runtime history unresolved: "
                            + ", ".join(reasons)
                        )
                partition = partition_runtime_effect_windows(
                    stream.final_state.windows,
                    at_time_seconds=snapshot,
                )
                if not any(
                    window.effect_name == effect.name for window in partition.active
                ):
                    continue
                buff = self._named_buff(effect)
                if buff is not None:
                    active_buffs.append(buff)
                else:
                    active_effects.append(effect)

        unique_effects: dict[tuple[str, str, float | None], EffectVariant] = {}
        for effect in active_effects:
            unique_effects[(str(effect.source), str(effect.name), effect.magnitude)] = effect

        return ExtremeSkillRuntimeEffectResult(
            active_buffs=tuple(dict.fromkeys(active_buffs)),
            active_effects=tuple(unique_effects.values()),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeSkillRuntimeEffectResult",
    "ExtremeSkillRuntimeEffectService",
]
