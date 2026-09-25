from __future__ import annotations

"""Finite weapon-enchantment source/cooldown sequence frontier for Objective #32.

The service owns deterministic timeline branching only. Cooldown duration and shared
cooldown identity must arrive as explicit authoritative policy evidence; no cadence,
identity sharing, or main/off-hand preference is inferred here.
"""

from dataclasses import dataclass
import math

from minmax.character_build.effect_instance import EffectVariant
from minmax.runtime_effect_sequence import (
    RuntimeEffectEventAttempt,
    effect_variant_runtime_binding_key,
)
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_weapon_enchantment_source_ownership_service import (
    ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy:
    effect: EffectVariant
    cooldown_identity: str
    cooldown_seconds: float
    authoritative: bool
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        identity = str(self.cooldown_identity or "").strip()
        if not identity:
            raise ValueError("weapon-enchantment cooldown policy requires cooldown_identity")
        cooldown = float(self.cooldown_seconds)
        if not math.isfinite(cooldown) or cooldown < 0.0:
            raise ValueError(
                "weapon-enchantment cooldown policy requires finite non-negative cooldown_seconds"
            )
        if not isinstance(self.authoritative, bool):
            raise TypeError(
                "weapon-enchantment cooldown policy authoritative must be boolean"
            )
        if not isinstance(self.effect, EffectVariant):
            raise TypeError(
                "weapon-enchantment cooldown policy effect must be canonical EffectVariant"
            )
        object.__setattr__(self, "cooldown_identity", identity)
        object.__setattr__(self, "cooldown_seconds", cooldown)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentSequenceChoice:
    choice_id: str
    attempts: tuple[RuntimeEffectEventAttempt, ...]
    no_proc_events: tuple[RuntimeEvent, ...]
    last_activation_times: tuple[tuple[str, float], ...]
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        choice_id = str(self.choice_id or "").strip()
        if not choice_id:
            raise ValueError("weapon-enchantment sequence choice requires choice_id")
        if any(
            not isinstance(row, RuntimeEffectEventAttempt)
            for row in self.attempts
        ):
            raise TypeError(
                "weapon-enchantment sequence attempts must contain runtime effect attempts"
            )
        if any(not isinstance(row, RuntimeEvent) for row in self.no_proc_events):
            raise TypeError(
                "weapon-enchantment sequence no_proc_events must contain RuntimeEvent records"
            )

        normalized_times: list[tuple[str, float]] = []
        seen: set[str] = set()
        for row in self.last_activation_times:
            if not isinstance(row, (tuple, list)) or len(row) != 2:
                raise TypeError(
                    "weapon-enchantment last activation rows must be (identity, time) pairs"
                )
            identity = str(row[0] or "").strip()
            if not identity:
                raise ValueError(
                    "weapon-enchantment last activation identity cannot be empty"
                )
            if identity in seen:
                raise ValueError(
                    "weapon-enchantment last activation identities must be unique"
                )
            seen.add(identity)
            if isinstance(row[1], bool):
                raise TypeError(
                    "weapon-enchantment last activation time must be numeric"
                )
            try:
                timestamp = float(row[1])
            except (TypeError, ValueError):
                raise TypeError(
                    "weapon-enchantment last activation time must be numeric"
                ) from None
            if not math.isfinite(timestamp) or timestamp < 0.0:
                raise ValueError(
                    "weapon-enchantment last activation time must be finite and non-negative"
                )
            normalized_times.append((identity, timestamp))

        object.__setattr__(self, "choice_id", choice_id)
        object.__setattr__(self, "attempts", tuple(self.attempts))
        object.__setattr__(self, "no_proc_events", tuple(self.no_proc_events))
        object.__setattr__(
            self,
            "last_activation_times",
            tuple(sorted(normalized_times)),
        )
        object.__setattr__(
            self,
            "evidence",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.evidence
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentSequenceFrontier:
    choices: tuple[ExtremeSustainedDPSWeaponEnchantmentSequenceChoice, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(
            not isinstance(
                row,
                ExtremeSustainedDPSWeaponEnchantmentSequenceChoice,
            )
            for row in self.choices
        ):
            raise TypeError(
                "weapon-enchantment sequence choices must contain canonical sequence choices"
            )
        if (
            isinstance(self.candidate_count, bool)
            or not isinstance(self.candidate_count, int)
            or self.candidate_count < 0
        ):
            raise ValueError(
                "weapon-enchantment sequence candidate_count must be a non-negative integer"
            )
        if self.candidate_count != len(self.choices):
            raise ValueError(
                "weapon-enchantment sequence candidate_count must equal choice count"
            )
        if not isinstance(self.denominator_proven, bool):
            raise TypeError(
                "weapon-enchantment sequence denominator_proven must be boolean"
            )

        evidence = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.evidence
                if str(item).strip()
            )
        )
        unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.unresolved
                if str(item).strip()
            )
        )
        if self.denominator_proven and (not self.choices or unresolved):
            raise ValueError(
                "weapon-enchantment sequence denominator cannot be proven with no choices or unresolved evidence"
            )
        object.__setattr__(self, "choices", tuple(self.choices))
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "unresolved", unresolved)


@dataclass(frozen=True)
class _Branch:
    attempts: tuple[RuntimeEffectEventAttempt, ...] = ()
    no_proc_events: tuple[RuntimeEvent, ...] = ()
    last_activation_times: tuple[tuple[str, float], ...] = ()
    evidence: tuple[str, ...] = ()

    def last_activation(self, identity: str) -> float | None:
        for candidate, timestamp in self.last_activation_times:
            if candidate == identity:
                return timestamp
        return None

    def with_activation(
        self,
        *,
        event: RuntimeEvent,
        effect: EffectVariant,
        policy: ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy,
    ) -> "_Branch":
        updated = dict(self.last_activation_times)
        updated[policy.cooldown_identity] = float(event.time_seconds)
        return _Branch(
            attempts=(
                *self.attempts,
                RuntimeEffectEventAttempt.for_bound_effect(
                    event=event,
                    effect=effect,
                ),
            ),
            no_proc_events=self.no_proc_events,
            last_activation_times=tuple(sorted(updated.items())),
            evidence=(
                *self.evidence,
                f"{event.time_seconds:g}s #{event.sequence}: {effect.source} selected",
            ),
        )

    def with_no_proc(self, event: RuntimeEvent) -> "_Branch":
        return _Branch(
            attempts=self.attempts,
            no_proc_events=(*self.no_proc_events, event),
            last_activation_times=self.last_activation_times,
            evidence=(
                *self.evidence,
                f"{event.time_seconds:g}s #{event.sequence}: all source-owned enchantments on cooldown",
            ),
        )


class ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService:
    """Enumerate every materially distinct exact enchantment source history."""

    def __init__(self, *, ownership_service: object | None = None) -> None:
        self.ownership_service = (
            ownership_service
            or ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService()
        )

    @staticmethod
    def _policy_map(
        *,
        effects: tuple[EffectVariant, ...],
        policies: tuple[ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy, ...],
    ) -> tuple[
        dict[
            tuple[str, str, str, str],
            ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy,
        ],
        tuple[str, ...],
    ]:
        effect_keys = {
            effect_variant_runtime_binding_key(effect)
            for effect in effects
        }
        rows: dict[
            tuple[str, str, str, str],
            ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy,
        ] = {}
        unresolved: list[str] = []
        for policy in policies:
            key = effect_variant_runtime_binding_key(policy.effect)
            if key not in effect_keys:
                unresolved.append(
                    "weapon-enchantment cooldown policy contains an effect outside the candidate universe"
                )
                continue
            existing = rows.get(key)
            if existing is not None:
                if (
                    existing.cooldown_identity != policy.cooldown_identity
                    or abs(
                        float(existing.cooldown_seconds)
                        - float(policy.cooldown_seconds)
                    )
                    > 1e-12
                    or existing.authoritative != policy.authoritative
                ):
                    unresolved.append(
                        "conflicting weapon-enchantment cooldown policies for one effect source"
                    )
                continue
            if not policy.authoritative:
                unresolved.append(
                    f"weapon-enchantment cooldown policy is not authoritative: {policy.effect.source}"
                )
            rows[key] = policy

        missing = effect_keys.difference(rows)
        if missing:
            unresolved.append(
                "authoritative cooldown policy is missing for one or more weapon-enchantment sources"
            )
        return rows, tuple(dict.fromkeys(unresolved))

    def build(
        self,
        *,
        events: tuple[RuntimeEvent, ...],
        effects: tuple[EffectVariant, ...],
        policies: tuple[
            ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy, ...
        ],
        event_denominator_proven: bool,
        source: str,
    ) -> ExtremeSustainedDPSWeaponEnchantmentSequenceFrontier:
        unresolved: list[str] = []
        if not event_denominator_proven:
            unresolved.append(
                "weapon-enchantment activation-event denominator is not proven complete"
            )

        policy_by_effect, policy_unresolved = self._policy_map(
            effects=tuple(effects),
            policies=tuple(policies),
        )
        unresolved.extend(policy_unresolved)
        effect_keys = {
            effect_variant_runtime_binding_key(effect)
            for effect in tuple(effects)
        }

        ordered_events = tuple(
            sorted(
                events,
                key=lambda event: (
                    float(event.time_seconds),
                    int(event.sequence),
                ),
            )
        )
        branches: tuple[_Branch, ...] = (_Branch(),)

        if not unresolved:
            for event in ordered_events:
                ownership = self.ownership_service.resolve(
                    activation_event=event,
                    enchantment_effects=tuple(effects),
                )
                if ownership.unresolved:
                    unresolved.extend(tuple(ownership.unresolved))
                    break

                next_branches: list[_Branch] = []
                for branch in branches:
                    ready: list[
                        tuple[
                            EffectVariant,
                            ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy,
                        ]
                    ] = []
                    for effect in tuple(ownership.candidates):
                        policy = policy_by_effect[
                            effect_variant_runtime_binding_key(effect)
                        ]
                        last = branch.last_activation(policy.cooldown_identity)
                        ready_at = (
                            None
                            if last is None
                            else last + float(policy.cooldown_seconds)
                        )
                        if ready_at is None or (
                            float(event.time_seconds) + 1e-12 >= ready_at
                        ):
                            ready.append((effect, policy))

                    if not ready:
                        next_branches.append(branch.with_no_proc(event))
                        continue

                    for effect, policy in ready:
                        next_branches.append(
                            branch.with_activation(
                                event=event,
                                effect=effect,
                                policy=policy,
                            )
                        )

                branches = tuple(next_branches)

        deduped: list[_Branch] = []
        seen: set[tuple[object, ...]] = set()
        for branch in branches:
            signature = (
                tuple(
                    (
                        attempt.event.time_seconds,
                        attempt.event.sequence,
                        attempt.bound_effect_key,
                    )
                    for attempt in branch.attempts
                ),
                tuple(
                    (event.time_seconds, event.sequence)
                    for event in branch.no_proc_events
                ),
                branch.last_activation_times,
            )
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(branch)

        choices = tuple(
            ExtremeSustainedDPSWeaponEnchantmentSequenceChoice(
                choice_id=f"weapon-enchantment-sequence:{index}",
                attempts=branch.attempts,
                no_proc_events=branch.no_proc_events,
                last_activation_times=branch.last_activation_times,
                evidence=branch.evidence,
            )
            for index, branch in enumerate(deduped)
        )
        deduped_unresolved = tuple(dict.fromkeys(unresolved))
        complete = bool(
            choices
            and event_denominator_proven
            and not deduped_unresolved
        )
        return ExtremeSustainedDPSWeaponEnchantmentSequenceFrontier(
            choices=choices,
            candidate_count=len(choices),
            denominator_proven=complete,
            evidence=(
                f"Weapon-enchantment activation events supplied: {len(ordered_events)}",
                f"Weapon-enchantment consequence variants supplied: {len(effects)}",
                f"Distinct weapon-enchantment sources supplied: {len(effect_keys)}",
                f"Authoritative cooldown policies supplied: {len(policies)}",
                f"Finite weapon-enchantment source histories: {len(choices)}",
                f"Weapon-enchantment sequence source: {str(source or '').strip() or 'caller-supplied proof'}",
                (
                    "Weapon-enchantment source/cooldown sequence denominator is proven finite"
                    if complete
                    else "Weapon-enchantment source/cooldown sequence denominator remains open"
                ),
            ),
            unresolved=deduped_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy",
    "ExtremeSustainedDPSWeaponEnchantmentSequenceChoice",
    "ExtremeSustainedDPSWeaponEnchantmentSequenceFrontier",
    "ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService",
]
