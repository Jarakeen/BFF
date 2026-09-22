from __future__ import annotations

"""Explicit finite encounter-policy families for sustained-DPS generated search."""

from dataclasses import dataclass

from minmax.rotation_demand_window import RotationDemandWindow


@dataclass(frozen=True)
class ExtremeSustainedDPSEncounterPolicyChoice:
    policy_id: str
    demands: tuple[RotationDemandWindow, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        policy_id = str(self.policy_id or "").strip()
        if not policy_id:
            raise ValueError("encounter-policy choice requires policy_id")
        object.__setattr__(self, "policy_id", policy_id)
        object.__setattr__(self, "demands", tuple(self.demands))
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSEncounterPolicyFrontier:
    choices: tuple[ExtremeSustainedDPSEncounterPolicyChoice, ...]
    candidate_count: int
    denominator_proven: bool
    omitted_scope: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSEncounterPolicyFrontierService:
    """Validate one caller-proven finite encounter-policy denominator."""

    @classmethod
    def build(
        cls,
        choices: tuple[ExtremeSustainedDPSEncounterPolicyChoice, ...],
        *,
        denominator_proven: bool,
        source: str,
        omitted_scope: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSEncounterPolicyFrontier:
        rows: list[ExtremeSustainedDPSEncounterPolicyChoice] = []
        unresolved: list[str] = []
        seen: set[str] = set()

        for choice in choices:
            key = choice.policy_id.casefold()
            if key in seen:
                unresolved.append(
                    f"Duplicate sustained-DPS encounter-policy identity: {choice.policy_id}"
                )
                continue
            seen.add(key)
            rows.append(choice)
            unresolved.extend(
                f"{choice.policy_id}: {item}"
                for item in choice.unresolved
            )

        if not rows:
            unresolved.append("Finite sustained-DPS encounter-policy family is empty")
        if not denominator_proven:
            unresolved.append(
                "Finite sustained-DPS encounter-policy denominator is not externally proven complete"
            )

        omitted = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in omitted_scope
                if str(item).strip()
            )
        )
        deduped = tuple(dict.fromkeys(unresolved))
        complete = bool(rows and denominator_proven and not deduped)

        return ExtremeSustainedDPSEncounterPolicyFrontier(
            choices=tuple(rows),
            candidate_count=len(rows),
            denominator_proven=complete,
            omitted_scope=omitted,
            evidence=(
                f"Finite encounter-policy choices retained: {len(rows)}",
                f"Encounter-policy denominator source: {str(source or '').strip() or 'caller-supplied proof'}",
                (
                    "Canonical encounter_policy denominator is locally proven"
                    if complete
                    else "Canonical encounter_policy denominator remains open"
                ),
                "Demand windows are explicit canonical RotationDemandWindow values; this service invents no encounter timing",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSEncounterPolicyChoice",
    "ExtremeSustainedDPSEncounterPolicyFrontier",
    "ExtremeSustainedDPSEncounterPolicyFrontierService",
]
