from __future__ import annotations

"""Exact runtime/recipient review for Ultimate sources on the recovery route."""

from dataclasses import dataclass
from enum import Enum


class UltimateSourceRuntimeStatus(str, Enum):
    COMPATIBLE_INCREMENT = "compatible_increment"
    SELF_INCOMPATIBLE = "self_incompatible"
    ROUTE_INCOMPATIBLE = "route_incompatible"
    SEARCH_STATE_MUTATION = "search_state_mutation"
    CANONICAL_EVIDENCE_REQUIRED = "canonical_evidence_required"


@dataclass(frozen=True)
class VampireHealthRecoveryTradeoff:
    shared_non_strategic_lower_bound: float
    non_vampire_incumbent_lower_bound: float
    vampire_candidate_best_case: float
    vampire_delta_upper_bound: float
    dominated: bool


@dataclass(frozen=True)
class UltimateSourceRuntimeReview:
    source_id: str
    status: UltimateSourceRuntimeStatus
    reason: str
    generated_ultimate_ceiling: float = 0.0
    remaining_ultimate_gap: float = 0.0


class UltimateSourceRuntimeLegalityService:
    """Apply reviewed canonical targeting and timing without scoring equipment."""

    _SEARCH_MUTATIONS = frozenset(
        {
            "exhilarating_drain",
            "bloodspawn",
            "baron_zaudrus",
            "hide_of_the_werewolf",
            "arkasis",
            "arkays_charity",
            "decisive",
        }
    )

    _BOUNDED_MUTATIONS = {
        "bloodspawn": (
            13.0,
            5.0,
            ("6|r% chance", "0-13 ultimate", "once every |cffffff5|r seconds"),
        ),
        "baron_zaudrus": (
            4.0,
            1.0,
            ("gain 3 stacks", "gain 4 ultimate", "1|r second"),
        ),
        "hide_of_the_werewolf": (
            6.0,
            5.0,
            ("generate 6 ultimate", "once every |cffffff5|r seconds"),
        ),
        "arkasis": (
            44.0,
            30.0,
            ("gain |cffffff1-44|r ultimate", "once every |cffffff30|r seconds"),
        ),
        "arkays_charity": (
            13.0,
            9.0,
            ("restore |cffffff13|r ultimate", "once every |cffffff9|r seconds"),
        ),
    }

    @staticmethod
    def _contains(records: tuple[str, ...], *fragments: str) -> bool:
        text = "\n".join(records).casefold()
        return all(fragment.casefold() in text for fragment in fragments)

    @staticmethod
    def assess_vampire_health_recovery_tradeoff(
        *,
        shared_non_strategic_lower_bound: float,
        incumbent_strategic_recovery: float,
        candidate_strategic_recovery: float,
        vampire_health_recovery_penalty_percent: float,
    ) -> VampireHealthRecoveryTradeoff:
        shared = max(0.0, float(shared_non_strategic_lower_bound))
        incumbent = max(0.0, float(incumbent_strategic_recovery))
        candidate = max(0.0, float(candidate_strategic_recovery))
        penalty = float(vampire_health_recovery_penalty_percent)
        if not 0.0 <= penalty <= 100.0:
            raise ValueError("Vampire Health Recovery penalty must be between 0 and 100")
        non_vampire = shared + incumbent
        vampire = (shared + candidate) * (1.0 - penalty / 100.0)
        delta = vampire - non_vampire
        return VampireHealthRecoveryTradeoff(
            shared_non_strategic_lower_bound=shared,
            non_vampire_incumbent_lower_bound=non_vampire,
            vampire_candidate_best_case=vampire,
            vampire_delta_upper_bound=delta,
            dominated=delta < -1e-9,
        )

    @classmethod
    def review(
        cls,
        source_id: str,
        *,
        canonical_records: tuple[str, ...] = (),
        required_additional_ultimate: float = 114.0,
        booming_voice_cast_seconds: float = 0.0,
        score_seconds: float = 24.999,
        trigger_seconds: tuple[float, ...] = (),
    ) -> UltimateSourceRuntimeReview:
        source_id = str(source_id or "").strip()
        gap = max(0.0, float(required_additional_ultimate))

        if source_id == "pillagers_profit":
            if not cls._contains(canonical_records, "other group members"):
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "The canonical recipient clause is missing.",
                    remaining_ultimate_gap=gap,
                )
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.SELF_INCOMPATIBLE,
                "The set grants Ultimate to other group members, not the caster whose Strategic Reserve is scored.",
                remaining_ultimate_gap=gap,
            )

        if source_id == "cryptcanon_vestments":
            if not cls._contains(canonical_records, "can no longer cast ultimate abilities"):
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "The canonical Ultimate-cast restriction is missing.",
                    remaining_ultimate_gap=gap,
                )
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.ROUTE_INCOMPATIBLE,
                "The mythic prevents the Ultimate cast required to start Booming Voice.",
                remaining_ultimate_gap=gap,
            )

        if source_id == "blessing_peak":
            if not cls._contains(
                canonical_records,
                "generate |cffffff1|r ultimate",
                "once every |cffffff6|r seconds",
            ):
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "The canonical amount and six-second cadence are missing.",
                    remaining_ultimate_gap=gap,
                )
            ordered = tuple(sorted(float(value) for value in trigger_seconds))
            legal_window = all(
                float(booming_voice_cast_seconds) < value <= float(score_seconds)
                for value in ordered
            )
            legal_cadence = all(
                later - earlier >= 6.0 - 1e-9
                for earlier, later in zip(ordered, ordered[1:])
            )
            if not ordered or not legal_window or not legal_cadence:
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "A legal post-cast Earthen Heart trigger witness is required.",
                    remaining_ultimate_gap=gap,
                )
            generated = float(len(ordered))
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.COMPATIBLE_INCREMENT,
                "The pure Dragonknight route can trigger the passive at the supplied legal six-second cadence.",
                generated_ultimate_ceiling=generated,
                remaining_ultimate_gap=max(0.0, gap - generated),
            )

        if source_id == "exhilarating_drain" and canonical_records:
            if not cls._contains(
                canonical_records,
                "generating |cffffff5|r ultimate every |cffffff1|r second",
                "for |cffffff3|r seconds",
            ):
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "The maximum-rank five-per-second channel record is missing.",
                    remaining_ultimate_gap=gap,
                )
            ordered = tuple(sorted(float(value) for value in trigger_seconds))
            legal_window = all(
                float(booming_voice_cast_seconds) < value <= float(score_seconds)
                for value in ordered
            )
            one_second_ticks = all(
                later - earlier >= 1.0 - 1e-9
                for earlier, later in zip(ordered, ordered[1:])
            )
            if not ordered or not legal_window or not one_second_ticks:
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "A legal post-cast one-second channel-tick witness is required.",
                    remaining_ultimate_gap=gap,
                )
            generated = 5.0 * float(len(ordered))
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION,
                "The supplied channel timeline establishes a hard ceiling; Vampire Health Recovery penalties and action occupancy remain unresolved.",
                generated_ultimate_ceiling=generated,
                remaining_ultimate_gap=max(0.0, gap - generated),
            )

        if source_id == "decisive" and canonical_records:
            if not cls._contains(
                canonical_records,
                "effect_type='ultimate_gain_chance'",
                "value=19.1",
                "secondary_value=1.0",
            ):
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "The canonical proc chance and one-Ultimate increment are missing.",
                    remaining_ultimate_gap=gap,
                )
            opportunities = tuple(float(value) for value in trigger_seconds)
            if not opportunities or any(
                not (
                    float(booming_voice_cast_seconds)
                    < value
                    <= float(score_seconds)
                )
                for value in opportunities
            ):
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "Explicit qualifying Ultimate-gain event opportunities are required.",
                    remaining_ultimate_gap=gap,
                )
            generated = float(len(opportunities))
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION,
                "One extra Ultimate per supplied qualifying event is the all-procs ceiling at 19.1%; it is not deterministic generation.",
                generated_ultimate_ceiling=generated,
                remaining_ultimate_gap=max(0.0, gap - generated),
            )

        if source_id in cls._BOUNDED_MUTATIONS and canonical_records:
            amount, cadence, fragments = cls._BOUNDED_MUTATIONS[source_id]
            if not cls._contains(canonical_records, *fragments):
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "The canonical amount, trigger, or cooldown clause is missing.",
                    remaining_ultimate_gap=gap,
                )
            ordered = tuple(sorted(float(value) for value in trigger_seconds))
            legal_window = all(
                float(booming_voice_cast_seconds) < value <= float(score_seconds)
                for value in ordered
            )
            legal_cadence = all(
                later - earlier >= cadence - 1e-9
                for earlier, later in zip(ordered, ordered[1:])
            )
            if not ordered or not legal_window or not legal_cadence:
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "A legal post-cast trigger witness respecting the canonical cooldown is required.",
                    remaining_ultimate_gap=gap,
                )
            generated = float(len(ordered)) * amount
            chance_note = (
                " This is a maximum-proc ceiling, not deterministic proc proof."
                if source_id == "bloodspawn"
                else ""
            )
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION,
                "The supplied timeline establishes a hard window ceiling; whole-build equipment dominance remains unresolved."
                + chance_note,
                generated_ultimate_ceiling=generated,
                remaining_ultimate_gap=max(0.0, gap - generated),
            )

        if source_id in cls._SEARCH_MUTATIONS:
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION,
                "Exact runtime evidence is compatible with continued review, but the source changes skill, Vampire, gear, or weapon-trait state.",
                remaining_ultimate_gap=gap,
            )

        return UltimateSourceRuntimeReview(
            source_id,
            UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
            "No exact runtime-legality rule owns this source.",
            remaining_ultimate_gap=gap,
        )


__all__ = [
    "UltimateSourceRuntimeLegalityService",
    "VampireHealthRecoveryTradeoff",
    "UltimateSourceRuntimeReview",
    "UltimateSourceRuntimeStatus",
]
