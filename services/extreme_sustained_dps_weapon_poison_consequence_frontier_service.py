from __future__ import annotations

"""Bind finite selected weapon-poison proc histories to explicit runtime consequences.

The poison sequence frontier owns chance and the player-global cooldown. This service
owns neither. It asks a caller-supplied authoritative consequence resolver what each
selected poison proc does, then converts those consequences into source-bound runtime
attempts so the ordinary runtime-state machinery can consume them.
"""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_target_type import SupportTargetType
from services.extreme_sustained_dps_runtime_attempt_evidence_frontier_service import (
    ExtremeSustainedDPSRuntimeAttemptEvidenceChoice,
    ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier,
)
from services.extreme_sustained_dps_weapon_poison_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonProcOccurrence,
    ExtremeSustainedDPSWeaponPoisonSequenceFrontier,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonConsequenceFrontierResult:
    attempt_frontier: ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier | None
    effects: tuple[EffectVariant, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            self.attempt_frontier is not None
            and not isinstance(
                self.attempt_frontier,
                ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier,
            )
        ):
            raise TypeError("weapon-poison consequence result requires canonical attempt frontier")
        for field in ("effects", "evidence", "unresolved"):
            if not isinstance(getattr(self, field), tuple):
                raise TypeError(f"weapon-poison consequence result {field} must be a tuple")
        if any(not isinstance(row, EffectVariant) for row in self.effects):
            raise TypeError("weapon-poison consequence effects must contain EffectVariant records")
        if self.attempt_frontier is not None and not isinstance(
            self.attempt_frontier.denominator_proven,
            bool,
        ):
            raise TypeError("weapon-poison consequence denominator proof must be boolean")

    @property
    def resolved(self) -> bool:
        return (
            self.attempt_frontier is not None
            and self.attempt_frontier.denominator_proven
            and not self.unresolved
        )


class ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService:
    """Project selected poison procs into explicit bound runtime attempts."""

    def __init__(self, *, consequence_resolver: object) -> None:
        if consequence_resolver is None:
            raise ValueError(
                "weapon-poison consequence frontier requires authoritative consequence resolver"
            )
        self.consequence_resolver = consequence_resolver

    @staticmethod
    def _invoke(
        resolver: object,
        *,
        occurrence: ExtremeSustainedDPSWeaponPoisonProcOccurrence,
    ):
        method = getattr(resolver, "resolve", None)
        if callable(method):
            return method(
                poison_id=occurrence.poison_id,
                occurrence=occurrence,
            )
        if callable(resolver):
            return resolver(
                poison_id=occurrence.poison_id,
                occurrence=occurrence,
            )
        raise TypeError(
            "weapon-poison consequence resolver must be callable or expose callable resolve()"
        )

    @staticmethod
    def _dedupe_effects(effects: list[EffectVariant]) -> tuple[EffectVariant, ...]:
        rows: list[EffectVariant] = []
        for effect in effects:
            if effect not in rows:
                rows.append(effect)
        return tuple(rows)

    @classmethod
    def _attempt_for(
        cls,
        occurrence: ExtremeSustainedDPSWeaponPoisonProcOccurrence,
        effect: EffectVariant,
    ) -> RuntimeEffectEventAttempt | None:
        trigger = str(effect.trigger or "").strip()
        if not trigger:
            return None
        event = RuntimeEvent(
            time_seconds=float(occurrence.event.time_seconds),
            sequence=int(occurrence.event.sequence),
            trigger=trigger,
            source=str(occurrence.poison_id or "").strip(),
            target=(
                None
                if effect.target_type is SupportTargetType.SELF
                else occurrence.event.target
            ),
            source_bar=occurrence.event.source_bar,
        )
        return RuntimeEffectEventAttempt.for_bound_effect(
            event=event,
            effect=effect,
            chance_roll=0.0,
        )

    def build(
        self,
        *,
        sequence_frontier: ExtremeSustainedDPSWeaponPoisonSequenceFrontier,
        source: str,
    ) -> ExtremeSustainedDPSWeaponPoisonConsequenceFrontierResult:
        if not isinstance(sequence_frontier.unresolved, tuple):
            raise TypeError("weapon-poison sequence unresolved evidence must be a tuple")
        if not isinstance(sequence_frontier.evidence, tuple):
            raise TypeError("weapon-poison sequence evidence must be a tuple")
        if not isinstance(sequence_frontier.choices, tuple):
            raise TypeError("weapon-poison sequence choices must be a tuple")
        if not isinstance(sequence_frontier.denominator_proven, bool):
            raise TypeError("weapon-poison sequence denominator proof must be boolean")
        unresolved: list[str] = list(sequence_frontier.unresolved)
        evidence: list[str] = list(sequence_frontier.evidence)
        all_effects: list[EffectVariant] = []
        choices: list[ExtremeSustainedDPSRuntimeAttemptEvidenceChoice] = []

        if not sequence_frontier.denominator_proven:
            unresolved.append(
                "weapon-poison consequence projection requires a proven sequence denominator"
            )

        for choice in tuple(sequence_frontier.choices):
            attempts: list[RuntimeEffectEventAttempt] = []
            choice_evidence: list[str] = list(tuple(choice.evidence))
            choice_unresolved: list[str] = []

            for occurrence in tuple(choice.procs):
                coordinate = (
                    f"{occurrence.event.time_seconds:g}s "
                    f"#{occurrence.event.sequence}"
                )
                try:
                    resolved = self._invoke(
                        self.consequence_resolver,
                        occurrence=occurrence,
                    )
                except (TypeError, ValueError) as exc:
                    choice_unresolved.append(
                        f"{coordinate}: {occurrence.poison_id} consequence resolver "
                        f"failed closed: {exc}"
                    )
                    continue

                result_unresolved_raw = getattr(resolved, "unresolved", ())
                result_evidence_raw = getattr(resolved, "evidence", ())
                effects = getattr(resolved, "effects", ())
                for field, value in (
                    ("unresolved", result_unresolved_raw),
                    ("evidence", result_evidence_raw),
                    ("effects", effects),
                ):
                    if not isinstance(value, tuple):
                        raise TypeError(
                            f"weapon-poison consequence resolver {field} must be a tuple"
                        )
                result_unresolved = tuple(
                    str(row).strip()
                    for row in result_unresolved_raw
                    if str(row).strip()
                )
                choice_unresolved.extend(
                    f"{coordinate}: {row}"
                    for row in result_unresolved
                )
                choice_evidence.extend(
                    str(row).strip()
                    for row in result_evidence_raw
                    if str(row).strip()
                )
                if not effects and not result_unresolved:
                    choice_unresolved.append(
                        f"{coordinate}: {occurrence.poison_id} consequence resolver "
                        "returned no explicit runtime effects"
                    )
                    continue

                for effect in effects:
                    if not isinstance(effect, EffectVariant):
                        choice_unresolved.append(
                            f"{coordinate}: {occurrence.poison_id} consequence resolver "
                            "returned a non-EffectVariant consequence"
                        )
                        continue
                    if effect.chance not in {None, 1.0}:
                        choice_unresolved.append(
                            f"{coordinate}: {occurrence.poison_id} consequence effect "
                            f"{effect.name} carries an extra proc chance after poison "
                            "chance was already resolved"
                        )
                        continue
                    attempt = self._attempt_for(occurrence, effect)
                    if attempt is None:
                        choice_unresolved.append(
                            f"{coordinate}: {occurrence.poison_id} consequence effect "
                            f"{effect.name} has no explicit runtime trigger"
                        )
                        continue
                    all_effects.append(effect)
                    attempts.append(attempt)

            unresolved.extend(
                f"{choice.choice_id}: {row}"
                for row in choice_unresolved
            )
            choices.append(
                ExtremeSustainedDPSRuntimeAttemptEvidenceChoice(
                    choice_id=f"weapon-poison-consequence:{choice.choice_id}",
                    attempts=tuple(attempts),
                    evidence=(
                        *tuple(choice_evidence),
                        f"Weapon-poison selected procs in branch: {len(choice.procs)}",
                        f"Weapon-poison consequence attempts in branch: {len(attempts)}",
                        f"Weapon-poison branch probability: {choice.branch_probability:g}",
                    ),
                )
            )

        deduped_unresolved = tuple(
            dict.fromkeys(row for row in unresolved if str(row).strip())
        )
        complete = bool(choices) and sequence_frontier.denominator_proven and not deduped_unresolved
        attempt_frontier = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier(
            choices=tuple(choices),
            candidate_count=len(choices),
            denominator_proven=complete,
            evidence=(
                f"Weapon-poison consequence branches: {len(choices)}",
                f"Weapon-poison runtime consequence effects: {len(self._dedupe_effects(all_effects))}",
                f"Weapon-poison consequence source: {str(source or '').strip() or 'caller-supplied proof'}",
                (
                    "Weapon-poison consequence denominator is explicitly bound to runtime effects"
                    if complete
                    else "Weapon-poison consequence denominator remains open"
                ),
            ),
            unresolved=deduped_unresolved,
        )
        return ExtremeSustainedDPSWeaponPoisonConsequenceFrontierResult(
            attempt_frontier=attempt_frontier,
            effects=self._dedupe_effects(all_effects),
            evidence=(
                *tuple(evidence),
                *tuple(attempt_frontier.evidence),
            ),
            unresolved=deduped_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonConsequenceFrontierResult",
    "ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService",
]
