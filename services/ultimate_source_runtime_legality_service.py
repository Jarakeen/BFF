from __future__ import annotations

"""Exact runtime/recipient review for Ultimate sources on the recovery route."""

from dataclasses import dataclass
from enum import Enum
import math

from minmax.ultimate_resource_timeline import UltimateGenerationEvent


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
class DecisiveUltimateOpportunitySummary:
    generation_events_reviewed: int
    non_heroism_opportunities: int
    heroism_events_reviewed: int
    merged_heroism_opportunities: int
    total_opportunities: int
    proc_chance_percent: float
    all_procs_ultimate_ceiling: float
    expected_extra_ultimate: float


@dataclass(frozen=True)
class BaronZaudrusGapRequirement:
    required_ultimate_gap: float
    decisive_all_procs_ceiling: float
    residual_gap_after_decisive: float
    ultimate_per_baron_proc: float
    stacks_per_baron_proc: int
    minimum_baron_procs: int
    minimum_status_applications: int
    baron_ultimate_at_minimum_procs: float
    combined_ultimate_ceiling: float
    surplus_over_gap: float
    score_window_seconds: float
    minimum_average_status_applications_per_second: float
    closes_gap_at_all_procs_ceiling: bool


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

    @staticmethod
    def decisive_opportunities_from_generation_events(
        events: tuple[UltimateGenerationEvent, ...],
        *,
        booming_voice_cast_seconds: float = 0.0,
        score_seconds: float = 24.999,
        proc_chance_percent: float = 19.1,
    ) -> DecisiveUltimateOpportunitySummary:
        """Derive Decisive proc opportunities from explicit Ultimate-gain events.

        Minor and Major Heroism on the same timestamp are one merged Heroism gain
        opportunity for Decisive. Other source events remain separate opportunities,
        even when they happen to share that timestamp with Heroism.
        """

        cast = float(booming_voice_cast_seconds)
        score = float(score_seconds)
        chance = float(proc_chance_percent)
        if not math.isfinite(cast) or cast < 0.0:
            raise ValueError("Booming Voice cast time must be finite and non-negative")
        if not math.isfinite(score) or score <= cast:
            raise ValueError("score time must be finite and after the Booming Voice cast")
        if not 0.0 <= chance <= 100.0:
            raise ValueError("Decisive proc chance must be between 0 and 100")

        in_window = tuple(
            event
            for event in events
            if cast < float(event.time_seconds) <= score
        )
        heroism = tuple(
            event for event in in_window if "heroism" in event.source.casefold()
        )
        non_heroism = tuple(
            event for event in in_window if "heroism" not in event.source.casefold()
        )
        heroism_times = tuple(
            sorted({round(float(event.time_seconds), 9) for event in heroism})
        )
        total = len(non_heroism) + len(heroism_times)
        ceiling = float(total)
        return DecisiveUltimateOpportunitySummary(
            generation_events_reviewed=len(in_window),
            non_heroism_opportunities=len(non_heroism),
            heroism_events_reviewed=len(heroism),
            merged_heroism_opportunities=len(heroism_times),
            total_opportunities=total,
            proc_chance_percent=chance,
            all_procs_ultimate_ceiling=ceiling,
            expected_extra_ultimate=ceiling * chance / 100.0,
        )

    @staticmethod
    def baron_zaudrus_requirement_after_decisive(
        *,
        required_ultimate_gap: float,
        decisive_all_procs_ceiling: float,
        score_window_seconds: float,
        ultimate_per_baron_proc: float = 4.0,
        stacks_per_baron_proc: int = 3,
    ) -> BaronZaudrusGapRequirement:
        """Reduce the remaining Ultimate gap to Baron proc/status requirements."""

        gap = max(0.0, float(required_ultimate_gap))
        decisive = max(0.0, float(decisive_all_procs_ceiling))
        window = float(score_window_seconds)
        per_proc = float(ultimate_per_baron_proc)
        stacks = int(stacks_per_baron_proc)
        if not math.isfinite(window) or window <= 0.0:
            raise ValueError("score window must be finite and greater than zero")
        if not math.isfinite(per_proc) or per_proc <= 0.0:
            raise ValueError("Baron Ultimate per proc must be finite and greater than zero")
        if stacks <= 0:
            raise ValueError("Baron stacks per proc must be greater than zero")

        residual = max(0.0, gap - decisive)
        minimum_procs = int(math.ceil(residual / per_proc - 1e-12)) if residual > 0.0 else 0
        applications = minimum_procs * stacks
        baron_ultimate = float(minimum_procs) * per_proc
        combined = decisive + baron_ultimate
        surplus = combined - gap
        return BaronZaudrusGapRequirement(
            required_ultimate_gap=gap,
            decisive_all_procs_ceiling=decisive,
            residual_gap_after_decisive=residual,
            ultimate_per_baron_proc=per_proc,
            stacks_per_baron_proc=stacks,
            minimum_baron_procs=minimum_procs,
            minimum_status_applications=applications,
            baron_ultimate_at_minimum_procs=baron_ultimate,
            combined_ultimate_ceiling=combined,
            surplus_over_gap=surplus,
            score_window_seconds=window,
            minimum_average_status_applications_per_second=(
                float(applications) / window
            ),
            closes_gap_at_all_procs_ceiling=combined >= gap - 1e-9,
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
    "BaronZaudrusGapRequirement",
    "DecisiveUltimateOpportunitySummary",
    "UltimateSourceRuntimeLegalityService",
    "VampireHealthRecoveryTradeoff",
    "UltimateSourceRuntimeReview",
    "UltimateSourceRuntimeStatus",
]
