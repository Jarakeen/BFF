from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremeMaximumHealUnresolvedRelevanceResult:
    relevant: tuple[str, ...]
    setup_prerequisites: tuple[str, ...]
    ambient: tuple[str, ...]

    @property
    def objective_complete(self) -> bool:
        return not self.relevant


class ExtremeMaximumHealUnresolvedRelevanceService:
    """Classify diagnostics for the Extreme achievable maximum-heal objective.

    Unknown diagnostics remain objective-relevant by default. A very small set of
    diagnostics may instead be classified as explicit setup prerequisites when the
    Extreme objective can deliberately construct that state before the healing
    event. This is intentionally different from a live-snapshot objective, where
    the same state may still require runtime proof.

    Reviewed setup prerequisites include summoning a legally slotted Sorcerer pet
    before using its special heal and activating a selected Spell Power potion
    before the target healing event. These requirements remain visible in the
    report but do not, by themselves, make an achievable-maximum candidate
    mechanically unprovable.

    Weapon traits such as Charged and Decisive remain relevant even when they do
    not directly alter a heal coefficient. Charged can alter status-effect state
    on targets, which may feed conditional healing/proc interactions. Decisive can
    alter Ultimate generation, which may change access to Ultimate heals or
    Ultimate-dependent passives/procs. Those state-space effects belong to the
    maximum-heal proof boundary rather than ambient character-sheet noise.
    """

    _SETUP_PREREQUISITE_SUBSTRINGS = (
        "sorcerer pet special activation requires runtime proof that the corresponding pet is summoned and alive",
        "potion selected; activation/uptime is not part of static build state: spell power",
    )

    _AMBIENT_SUBSTRINGS = (
        "champion point is dynamic or not yet stat-mapped: master gatherer",
        "champion point is dynamic or not yet stat-mapped: celerity",
        "movement_speed unresolved",
        "training: non-combat experience trait",
    )

    def classify(self, unresolved) -> ExtremeMaximumHealUnresolvedRelevanceResult:
        relevant: list[str] = []
        setup_prerequisites: list[str] = []
        ambient: list[str] = []
        for raw in tuple(unresolved or ()):
            message = str(raw or "").strip()
            if not message:
                continue
            key = message.casefold()
            if any(token in key for token in self._SETUP_PREREQUISITE_SUBSTRINGS):
                setup_prerequisites.append(message)
            elif any(token in key for token in self._AMBIENT_SUBSTRINGS):
                ambient.append(message)
            else:
                relevant.append(message)
        return ExtremeMaximumHealUnresolvedRelevanceResult(
            relevant=tuple(dict.fromkeys(relevant)),
            setup_prerequisites=tuple(dict.fromkeys(setup_prerequisites)),
            ambient=tuple(dict.fromkeys(ambient)),
        )
