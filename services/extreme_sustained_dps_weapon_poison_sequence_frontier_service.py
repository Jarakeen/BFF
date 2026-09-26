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

    def __post_init__(self) -> None:
        if not isinstance(self.event, RuntimeEvent):
            raise TypeError("weapon-poison proc occurrence requires RuntimeEvent")
        poison_id = str(self.poison_id or "").strip()
        if not poison_id:
            raise ValueError("weapon-poison proc occurrence requires poison_id")
        object.__setattr__(self, "poison_id", poison_id)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonSequenceChoice:
    choice_id: str
    procs: tuple[ExtremeSustainedDPSWeaponPoisonProcOccurrence, ...]
    chance_misses: tuple[RuntimeEvent, ...]
    cooldown_blocked: tuple[RuntimeEvent, ...]
    last_proc_time_seconds: float | None
    branch_probability: float
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        choice_id = str(self.choice_id or "").strip()
        if not choice_id:
            raise ValueError("weapon-poison sequence choice requires choice_id")
        if any(
            not isinstance(row, ExtremeSustainedDPSWeaponPoisonProcOccurrence)
            for row in self.procs
        ):
            raise TypeError(
                "weapon-poison sequence procs must contain canonical proc occurrences"
            )
        if any(not isinstance(row, RuntimeEvent) for row in self.chance_misses):
            raise TypeError(
                "weapon-poison chance_misses must contain RuntimeEvent records"
            )
        if any(not isinstance(row, RuntimeEvent) for row in self.cooldown_blocked):
            raise TypeError(
                "weapon-poison cooldown_blocked must contain RuntimeEvent records"
            )

        last_proc = self.last_proc_time_seconds
        if last_proc is not None:
            if isinstance(last_proc, bool):
                raise TypeError("weapon-poison last proc time must be numeric")
            try:
                last_proc = float(last_proc)
            except (TypeError, ValueError):
                raise TypeError("weapon-poison last proc time must be numeric") from None
            if not math.isfinite(last_proc) or last_proc < 0.0:
                raise ValueError(
                    "weapon-poison last proc time must be finite and non-negative"
                )

        probability = self.branch_probability
        if isinstance(probability, bool):
            raise TypeError("weapon-poison branch probability must be numeric")
        try:
            probability = float(probability)
        except (TypeError, ValueError):
            raise TypeError(
                "weapon-poison branch probability must be numeric"
            ) from None
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError(
                "weapon-poison branch probability must be finite and between 0 and 1"
            )

        object.__setattr__(self, "choice_id", choice_id)
        object.__setattr__(self, "procs", tuple(self.procs))
        object.__setattr__(self, "chance_misses", tuple(self.chance_misses))
        object.__setattr__(self, "cooldown_blocked", tuple(self.cooldown_blocked))
        object.__setattr__(self, "last_proc_time_seconds", last_proc)
        object.__setattr__(self, "branch_probability", probability)
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
class ExtremeSustainedDPSWeaponPoisonSequenceFrontier:
    choices: tuple[ExtremeSustainedDPSWeaponPoisonSequenceChoice, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(
            not isinstance(row, ExtremeSustainedDPSWeaponPoisonSequenceChoice)
            for row in self.choices
        ):
            raise TypeError(
                "weapon-poison sequence choices must contain canonical sequence choices"
            )
        if (
            isinstance(self.candidate_count, bool)
            or not isinstance(self.candidate_count, int)
            or self.candidate_count < 0
        ):
            raise ValueError(
                "weapon-poison sequence candidate_count must be a non-negative integer"
            )
        if self.candidate_count != len(self.choices):
            raise ValueError(
                "weapon-poison sequence candidate_count must equal choice count"
            )
        if not isinstance(self.denominator_proven, bool):
            raise TypeError(
                "weapon-poison sequence denominator_proven must be boolean"
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
                "weapon-poison sequence denominator cannot be proven with no choices or unresolved evidence"
            )
        object.__setattr__(self, "choices", tuple(self.choices))
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "unresolved", unresolved)


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
        if not isinstance(event_denominator_proven, bool):
            raise TypeError(
                "weapon-poison event_denominator_proven must be boolean"
            )
        if any(not isinstance(row, RuntimeEvent) for row in events):
            raise TypeError(
                "weapon-poison events must contain RuntimeEvent records"
            )
        if not isinstance(player_build, PlayerBuild):
            raise TypeError("weapon-poison sequence requires PlayerBuild")
        if not isinstance(self.cadence, WeaponPoisonCadenceEvidence):
            raise TypeError(
                "weapon-poison sequence cadence must be WeaponPoisonCadenceEvidence"
            )
        if not isinstance(self.cadence.runtime_ready, bool):
            raise TypeError(
                "weapon-poison cadence runtime_ready must be boolean"
            )
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
