from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.effect_layer import EffectLayer
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.named_combat_buffs import canonical_buff_name, effects_for_buff
from minmax.runtime_effect_eligibility import (
    RuntimeEffectState,
    evaluate_effect_variant_runtime_eligibility,
)
from minmax.runtime_event import RuntimeEvent, runtime_event_matches_effect_variant
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeActualHealGearRuntimeBuffResult:
    active_buffs: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class ExtremeActualHealGearRuntimeBuffService:
    """Resolve runtime-proven gear-set named buffs for one heal snapshot.

    Existing Extreme gear candidates own equipment search. This service only
    asks what verified proc effects the candidate's actually equipped sets can
    produce at the supplied runtime event and snapshot. It does not parse set
    descriptions or infer that ALLY/GROUP necessarily includes the wearer.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        repository: GearSetRepository | None = None,
        resolver: GearSetEffectVariantResolver | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.repository = repository or GearSetRepository(self.database_path)
        self.resolver = resolver or GearSetEffectVariantResolver(self.repository)

    @staticmethod
    def _named_buff(effect) -> str | None:
        if effect.layer is not EffectLayer.PROC:
            return None
        if effect.duration is None or float(effect.duration) <= 0.0:
            return None
        canonical = canonical_buff_name(str(effect.name or "").replace("_", " "))
        if canonical is None or not effects_for_buff(canonical):
            return None
        return canonical

    def resolve(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
        event: RuntimeEvent,
        snapshot_time_seconds: float,
        state: RuntimeEffectState = RuntimeEffectState(),
        chance_roll: float | None = None,
    ) -> ExtremeActualHealGearRuntimeBuffResult:
        snapshot = float(snapshot_time_seconds)
        if snapshot < event.time_seconds:
            raise ValueError("gear proc snapshot cannot precede the runtime event")
        elapsed = snapshot - event.time_seconds
        active: list[str] = []
        unresolved: list[str] = []

        counts = GearStatInputResolver.equipped_set_counts(build, active_bar=active_bar)
        for set_name, piece_count in sorted(counts.items(), key=lambda item: item[0].casefold()):
            gear_set = self.repository.get_set(set_name)
            if gear_set is None:
                continue
            for effect in self.resolver.resolve(gear_set.id, int(piece_count)):
                buff = self._named_buff(effect)
                if buff is None:
                    continue
                if not runtime_event_matches_effect_variant(event, effect):
                    continue
                if elapsed >= float(effect.duration):
                    continue

                if effect.condition is not None:
                    unresolved.append(
                        f"{set_name} {buff} runtime condition is not executable: {effect.condition}"
                    )
                    continue

                if effect.target_type is not SupportTargetType.SELF:
                    target = (
                        effect.target_type.value
                        if effect.target_type is not None
                        else "unclassified"
                    )
                    unresolved.append(
                        f"{set_name} {buff} proc target {target!r} does not canonically prove wearer self-application"
                    )
                    continue

                eligibility = evaluate_effect_variant_runtime_eligibility(
                    event,
                    effect,
                    state=state,
                    chance_roll=chance_roll,
                )
                if eligibility.eligible:
                    active.append(buff)
                elif eligibility.chance_roll_required:
                    unresolved.append(
                        f"{set_name} {buff} proc requires an explicit deterministic chance roll"
                    )

        return ExtremeActualHealGearRuntimeBuffResult(
            active_buffs=tuple(dict.fromkeys(active)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
