from __future__ import annotations

"""Finite weapon-poison chance/cooldown history frontier for Objective #32."""

from dataclasses import dataclass
import math

from minmax.runtime_event import RuntimeEvent
from minmax.weapon_poison_runtime_cadence import (
    WeaponPoisonCadenceEvidence,
    authoritative_weapon_poison_cadence,
)
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonProcOccurrence:
    event: RuntimeEvent
    poison_id: str


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonSequenceChoice:
    choice_id: str
    procs: tuple[ExtremeSustainedDPSWeaponPoisonProcOccurrence, ...]
    chance_misses: tuple[RuntimeEvent, ...]
    cooldown_blocked: tuple[RuntimeEvent, ...]
    last_proc_time_seconds: float | None
    branch_probability: float
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonSequenceFrontier:
    choices: tuple[ExtremeSustainedDPSWeaponPoisonSequenceChoice, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class _Branch:
    procs: tuple[ExtremeSustainedDPSWeaponPoisonProcOccurrence, ...] = ()
    chance_misses: tuple[RuntimeEvent, ...] = ()
    cooldown_blocked: tuple[RuntimeEvent, ...] = ()
    last_proc_time_seconds: float | None = None
    probability: float = 1.0
    evidence: tuple[str, ...] = ()


class ExtremeSustainedDPSWeaponPoisonSequenceFrontierService:
    """Enumerate every finite poison proc/miss history under the shared timer."""

    def __init__(
        self,
        *,
        cadence: WeaponPoisonCadenceEvidence | None = None,
    ) -> None:
        self.cadence = cadence or authoritative_weapon_poison_cadence()

    @staticmethod
    def _poison_for_bar(build: PlayerBuild, event: RuntimeEvent) -> str:
        if event.source_bar == "front":
            return str(getattr(build, "FrontBarPoison", "") or "").strip()
        if event.source_bar == "back":
            return str(getattr(build, "BackBarPoison", "") or "").strip()
        return ""

    def build(
        self,
        *,
        events: tuple[RuntimeEvent, ...],
        player_build: PlayerBuild,
        event_denominator_proven: bool,
        source: str,
    ) -> ExtremeSustainedDPSWeaponPoisonSequenceFrontier:
        unresolved: list[str] = []
        cadence = self.cadence
        if not event_denominator_proven:
            unresolved.append(
                "weapon-poison activation-event denominator is not proven complete"
            )
        unresolved.extend(tuple(cadence.runtime_blockers))

        try:
            proc_chance = float(cadence.proc_chance)
            cooldown = float(cadence.cooldown_seconds)
        except (TypeError, ValueError):
            proc_chance = math.nan
            cooldown = math.nan
        if not math.isfinite(proc_chance) or not 0.0 <= proc_chance <= 1.0:
            unresolved.append("weapon-poison proc chance is invalid")
        if not math.isfinite(cooldown) or cooldown < 0.0:
            unresolved.append("weapon-poison cooldown is invalid")

        ordered = tuple(
            sorted(
                events,
                key=lambda event: (
                    float(event.time_seconds),
                    int(event.sequence),
                    event.source.casefold(),
                ),
            )
        )
        branches: tuple[_Branch, ...] = (_Branch(),)

        if not unresolved:
            for event in ordered:
                poison_id = self._poison_for_bar(player_build, event)
                if not poison_id:
                    unresolved.append(
                        f"{event.time_seconds:g}s #{event.sequence}: poison event source "
                        "bar has no equipped poison"
                    )
                    break

                next_branches: list[_Branch] = []
                for branch in branches:
                    ready_at = (
                        None
                        if branch.last_proc_time_seconds is None
                        else float(branch.last_proc_time_seconds) + cooldown
                    )
                    if ready_at is not None and (
                        float(event.time_seconds) + 1e-12 < ready_at
                    ):
                        next_branches.append(
                            _Branch(
                                procs=branch.procs,
                                chance_misses=branch.chance_misses,
                                cooldown_blocked=(*branch.cooldown_blocked, event),
                                last_proc_time_seconds=branch.last_proc_time_seconds,
                                probability=branch.probability,
                                evidence=(
                                    *branch.evidence,
                                    f"{event.time_seconds:g}s #{event.sequence}: "
                                    "global poison cooldown blocks proc",
                                ),
                            )
                        )
                        continue

                    if proc_chance > 0.0:
                        next_branches.append(
                            _Branch(
                                procs=(
                                    *branch.procs,
                                    ExtremeSustainedDPSWeaponPoisonProcOccurrence(
                                        event=event,
                                        poison_id=poison_id,
                                    ),
                                ),
                                chance_misses=branch.chance_misses,
                                cooldown_blocked=branch.cooldown_blocked,
                                last_proc_time_seconds=float(event.time_seconds),
                                probability=branch.probability * proc_chance,
                                evidence=(
                                    *branch.evidence,
                                    f"{event.time_seconds:g}s #{event.sequence}: "
                                    f"{poison_id} procs",
                                ),
                            )
                        )
                    if proc_chance < 1.0:
                        next_branches.append(
                            _Branch(
                                procs=branch.procs,
                                chance_misses=(*branch.chance_misses, event),
                                cooldown_blocked=branch.cooldown_blocked,
                                last_proc_time_seconds=branch.last_proc_time_seconds,
                                probability=branch.probability * (1.0 - proc_chance),
                                evidence=(
                                    *branch.evidence,
                                    f"{event.time_seconds:g}s #{event.sequence}: "
                                    f"{poison_id} chance miss",
                                ),
                            )
                        )
                branches = tuple(next_branches)

        deduped: list[_Branch] = []
        seen: set[tuple[object, ...]] = set()
        for branch in branches:
            signature = (
                tuple(
                    (
                        row.event.time_seconds,
                        row.event.sequence,
                        row.event.source_bar,
                        row.poison_id,
                    )
                    for row in branch.procs
                ),
                tuple(
                    (row.time_seconds, row.sequence, row.source_bar)
                    for row in branch.chance_misses
                ),
                tuple(
                    (row.time_seconds, row.sequence, row.source_bar)
                    for row in branch.cooldown_blocked
                ),
                branch.last_proc_time_seconds,
            )
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(branch)

        choices = tuple(
            ExtremeSustainedDPSWeaponPoisonSequenceChoice(
                choice_id=f"weapon-poison-sequence:{index}",
                procs=branch.procs,
                chance_misses=branch.chance_misses,
                cooldown_blocked=branch.cooldown_blocked,
                last_proc_time_seconds=branch.last_proc_time_seconds,
                branch_probability=float(branch.probability),
                evidence=branch.evidence,
            )
            for index, branch in enumerate(deduped)
        )
        deduped_unresolved = tuple(dict.fromkeys(row for row in unresolved if row))
        complete = bool(
            choices
            and event_denominator_proven
            and cadence.runtime_ready
            and not deduped_unresolved
        )
        return ExtremeSustainedDPSWeaponPoisonSequenceFrontier(
            choices=choices,
            candidate_count=len(choices),
            denominator_proven=complete,
            evidence=(
                f"Weapon-poison activation events supplied: {len(ordered)}",
                f"Weapon-poison finite histories: {len(choices)}",
                f"Weapon-poison proc chance: {proc_chance:g}",
                f"Weapon-poison global cooldown: {cooldown:g}s",
                f"Weapon-poison sequence source: {str(source or '').strip() or 'caller-supplied proof'}",
                (
                    "Weapon-poison chance/cooldown denominator is proven finite"
                    if complete
                    else "Weapon-poison chance/cooldown denominator remains open"
                ),
            ),
            unresolved=deduped_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonProcOccurrence",
    "ExtremeSustainedDPSWeaponPoisonSequenceChoice",
    "ExtremeSustainedDPSWeaponPoisonSequenceFrontier",
    "ExtremeSustainedDPSWeaponPoisonSequenceFrontierService",
]
