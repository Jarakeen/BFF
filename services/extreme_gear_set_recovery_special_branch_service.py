from __future__ import annotations

"""Classify unresolved recovery-set mechanics into proof-owned semantic branches.

This layer owns classification only.  It does not score a character sheet and does
not infer that a runtime condition is active.  The purpose is to turn the small set
of recovery-relevant, mechanic-unmapped descriptions into explicit search branches
or explicit non-challengers without relying on a set-name allowlist.
"""

from dataclasses import dataclass
from enum import Enum
import re

from minmax.eso_markup import normalize_eso_markup


class ExtremeRecoverySpecialBranchKind(str, Enum):
    CONDITIONAL_FLAT = "conditional_flat"
    STACKED_FLAT = "stacked_flat"
    CONDITIONAL_PERCENT = "conditional_percent"
    FORMULA = "formula"
    NAMED_BUFF = "named_buff"
    NEGATIVE_ONLY = "negative_only"
    SELF_INELIGIBLE = "self_ineligible"
    SEARCH_STATE_MUTATION = "search_state_mutation"


@dataclass(frozen=True)
class ExtremeRecoverySpecialBranch:
    set_name: str
    piece_count: int
    kind: ExtremeRecoverySpecialBranchKind
    can_raise_self: bool
    flat_ceiling: float | None = None
    percent_ceiling: float | None = None
    condition: str | None = None
    search_state_rule: str | None = None
    description: str = ""


@dataclass(frozen=True)
class ExtremeRecoverySpecialBranchCatalog:
    branches: tuple[ExtremeRecoverySpecialBranch, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_classified(self) -> bool:
        return bool(self.branches) and not self.unresolved

    @property
    def positive_challengers(self) -> tuple[ExtremeRecoverySpecialBranch, ...]:
        return tuple(row for row in self.branches if row.can_raise_self)

    @property
    def reviewed_non_challengers(self) -> tuple[ExtremeRecoverySpecialBranch, ...]:
        return tuple(row for row in self.branches if not row.can_raise_self)


class ExtremeGearSetRecoverySpecialBranchService:
    """Description-driven recovery special classification with fail-closed fallback."""

    _SEARCH_STATE_PHRASES = (
        ("two mundus stone boons", "allows_two_mundus"),
        ("disable all other item set bonuses", "suppresses_other_set_bonuses"),
        ("unable to swap between your primary and backup weapon sets", "one_bar_only"),
    )

    @staticmethod
    def _text(description: str) -> str:
        return " ".join(normalize_eso_markup(str(description or "")).text.casefold().split())

    @staticmethod
    def _max_number(text: str) -> float | None:
        values = [float(value) for value in re.findall(r"(?<![%\d])\d+(?:\.\d+)?", text)]
        return max(values) if values else None

    @classmethod
    def classify(
        cls,
        *,
        set_name: str,
        piece_count: int,
        description: str,
        objective_key: str = "health_recovery",
    ) -> ExtremeRecoverySpecialBranch | None:
        key = str(objective_key or "").strip().casefold()
        if key not in {"health_recovery", "magicka_recovery", "stamina_recovery"}:
            raise KeyError(f"unreviewed recovery objective: {objective_key!r}")

        resource = {
            "health_recovery": "health",
            "magicka_recovery": "magicka",
            "stamina_recovery": "stamina",
        }[key]
        text = cls._text(description)
        if not text:
            return None

        for phrase, rule in cls._SEARCH_STATE_PHRASES:
            if phrase in text:
                can_raise = False
                percent = None
                if rule == "one_bar_only":
                    named = {
                        "health": "minor fortitude",
                        "magicka": "minor intellect",
                        "stamina": "minor endurance",
                    }[resource]
                    can_raise = named in text
                    percent = 15.0 if can_raise else None
                return ExtremeRecoverySpecialBranch(
                    set_name=set_name,
                    piece_count=int(piece_count),
                    kind=ExtremeRecoverySpecialBranchKind.SEARCH_STATE_MUTATION,
                    can_raise_self=can_raise,
                    percent_ceiling=percent,
                    condition=named if rule == "one_bar_only" and can_raise else None,
                    search_state_rule=rule,
                    description=description,
                )

        if "cannot affect yourself" in text or "cannot affect self" in text:
            return ExtremeRecoverySpecialBranch(
                set_name=set_name,
                piece_count=int(piece_count),
                kind=ExtremeRecoverySpecialBranchKind.SELF_INELIGIBLE,
                can_raise_self=False,
                description=description,
            )

        target_phrase = f"{resource} recovery"
        shared_recovery = (
            "health" in text and "magicka" in text and "stamina recovery" in text
        )
        relevant = target_phrase in text or shared_recovery
        named_buff = {
            "health": ("major fortitude", "minor fortitude"),
            "magicka": ("major intellect", "minor intellect"),
            "stamina": ("major endurance", "minor endurance"),
        }[resource]

        for phrase in named_buff:
            if phrase in text:
                percent = 30.0 if phrase.startswith("major") else 15.0
                return ExtremeRecoverySpecialBranch(
                    set_name=set_name,
                    piece_count=int(piece_count),
                    kind=ExtremeRecoverySpecialBranchKind.NAMED_BUFF,
                    can_raise_self=True,
                    percent_ceiling=percent,
                    condition=phrase.replace(" ", "_"),
                    description=description,
                )

        if not relevant:
            return None

        negative_markers = (
            "lowers the health recovery",
            "reducing their health recovery",
            "health recovery are reduced",
            "health recovery is reduced",
            "reduce your health, magicka, and stamina recovery",
        )
        if any(marker in text for marker in negative_markers):
            return ExtremeRecoverySpecialBranch(
                set_name=set_name,
                piece_count=int(piece_count),
                kind=ExtremeRecoverySpecialBranchKind.NEGATIVE_ONLY,
                can_raise_self=False,
                description=description,
            )

        if "sum total physical resistance and spell resistance" in text:
            cap_match = re.search(r"maximum of\s+(\d+(?:\.\d+)?)", text)
            ceiling = float(cap_match.group(1)) if cap_match else None
            return ExtremeRecoverySpecialBranch(
                set_name=set_name,
                piece_count=int(piece_count),
                kind=ExtremeRecoverySpecialBranchKind.FORMULA,
                can_raise_self=True,
                flat_ceiling=ceiling,
                condition="resistance_scaled",
                description=description,
            )

        percent_match = re.search(
            r"(?:increase(?:s|d)?|increasing)\s+(?:your\s+)?(?:health, magicka, and stamina recovery|"
            + re.escape(target_phrase)
            + r")\s+by\s+(\d+(?:\.\d+)?)%",
            text,
        )
        if percent_match:
            return ExtremeRecoverySpecialBranch(
                set_name=set_name,
                piece_count=int(piece_count),
                kind=ExtremeRecoverySpecialBranchKind.CONDITIONAL_PERCENT,
                can_raise_self=True,
                percent_ceiling=float(percent_match.group(1)),
                description=description,
            )

        # Repeated stack grammar has to be classified before generic flat grammar.
        stack_match = re.search(
            r"(?:up to\s+(\d+)\s+stacks|each stack[^.]{0,100}?(?:increases|increase)[^.]{0,120}?\sby\s+(\d+(?:\.\d+)?))",
            text,
        )
        if "stack" in text and relevant:
            numbers = [float(v) for v in re.findall(r"\b\d+(?:\.\d+)?\b", text)]
            if numbers:
                # For reviewed recovery stack descriptions the maximum additive
                # result is explicitly present either as an "up to" value or as
                # count x per-stack. Prefer an explicit recovery "up to" ceiling.
                up_to = re.search(r"recovery[^.]{0,80}?up to\s+(\d+(?:\.\d+)?)", text)
                ceiling = float(up_to.group(1)) if up_to else None
                if ceiling is None and stack_match:
                    counts = [int(v) for v in re.findall(r"up to\s+(\d+)\s+stacks", text)]
                    per_stack = re.search(r"each stack[^.]{0,120}?by\s+(\d+(?:\.\d+)?)", text)
                    if counts and per_stack:
                        ceiling = max(counts) * float(per_stack.group(1))
                if ceiling is not None:
                    return ExtremeRecoverySpecialBranch(
                        set_name=set_name,
                        piece_count=int(piece_count),
                        kind=ExtremeRecoverySpecialBranchKind.STACKED_FLAT,
                        can_raise_self=True,
                        flat_ceiling=ceiling,
                        condition="max_stacks",
                        description=description,
                    )

        # Flat conditional recovery descriptions typically use a range in the DB
        # (e.g. 35-1505) or an explicit fixed amount. Take the highest number tied
        # to the recovery clause as a challenger ceiling; later runtime scoring
        # owns the activation condition and exact stacking order.
        if relevant and any(word in text for word in ("gain ", "adds ", "increased by", "increase your", "receive ")):
            ranges = [float(v) for v in re.findall(r"(?:\d+(?:\.\d+)?)-(?P<hi>\d+(?:\.\d+)?)", text) for v in [v]]
            flat = max(ranges) if ranges else None
            if flat is None:
                nearby = re.findall(r"(?:gain|adds?|increased by|receive)\s+(\d+(?:\.\d+)?)", text)
                if nearby:
                    flat = max(float(v) for v in nearby)
            if flat is not None:
                return ExtremeRecoverySpecialBranch(
                    set_name=set_name,
                    piece_count=int(piece_count),
                    kind=ExtremeRecoverySpecialBranchKind.CONDITIONAL_FLAT,
                    can_raise_self=True,
                    flat_ceiling=flat,
                    condition="runtime_condition_required",
                    description=description,
                )

        return None

    @classmethod
    def build(cls, rows, *, objective_key: str = "health_recovery") -> ExtremeRecoverySpecialBranchCatalog:
        branches: list[ExtremeRecoverySpecialBranch] = []
        unresolved: list[str] = []
        for set_name, piece_count, description in rows:
            branch = cls.classify(
                set_name=str(set_name),
                piece_count=int(piece_count),
                description=str(description),
                objective_key=objective_key,
            )
            if branch is None:
                unresolved.append(f"{set_name} ({piece_count}): unclassified recovery mechanic")
            else:
                branches.append(branch)
        return ExtremeRecoverySpecialBranchCatalog(
            branches=tuple(sorted(branches, key=lambda row: (row.set_name.casefold(), row.piece_count))),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeGearSetRecoverySpecialBranchService",
    "ExtremeRecoverySpecialBranch",
    "ExtremeRecoverySpecialBranchCatalog",
    "ExtremeRecoverySpecialBranchKind",
]
