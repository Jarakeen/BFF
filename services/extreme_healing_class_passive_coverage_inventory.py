from __future__ import annotations

from dataclasses import dataclass

from minmax.passive_eligibility import CLASS_SKILL_LINES


REVIEWED = "reviewed"
PARTIAL = "partial"
UNREVIEWED = "unreviewed"
IMPLEMENTED = "implemented"
EXPLICITLY_UNSUPPORTED = "explicitly_unsupported"
NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class ExtremeHealingClassPassiveCoverageEntry:
    eso_class: str
    skill_line: str
    review_status: str
    healing_relevant: bool | None
    coverage_status: str
    implemented_hook: bool
    evidence: str
    detail: str

    @property
    def family_id(self) -> str:
        return f"{self.eso_class}:{self.skill_line}"


@dataclass(frozen=True)
class ExtremeHealingClassPassiveCoverageSummary:
    total_families: int
    reviewed_families: int
    partially_reviewed_families: int
    unreviewed_families: int
    healing_relevant_families: int
    implemented: int
    explicitly_unsupported: int
    healing_relevant_unreviewed: int
    implemented_hooks: int

    @property
    def complete(self) -> bool:
        return (
            self.reviewed_families == self.total_families
            and self.explicitly_unsupported == 0
            and self.healing_relevant_unreviewed == 0
        )


class ExtremeHealingClassPassiveCoverageInventory:
    """Canonical review denominator for healing-relevant class passive families.

    Every class skill-line family in ``CLASS_SKILL_LINES`` must appear exactly
    once. ``reviewed`` means the family has been exhaustively checked for every
    passive that can change the MOST Actual Heal objective. ``partial`` means
    concrete healing behavior is already modeled but the entire family has not
    yet earned that completeness claim. ``unreviewed`` means no family-level
    review has been recorded.

    Family coverage and individual implemented hooks are deliberately separate.
    A working hook inside a family must never promote the whole family to
    reviewed by implication.
    """

    _NO_REVIEW_EVIDENCE = "No completed Extreme healer class-passive review recorded"
    _NO_REVIEW_DETAIL = (
        "Class-passive relevance to MOST Actual Heal has not yet been reviewed."
    )

    _ENTRIES = (
        ExtremeHealingClassPassiveCoverageEntry("arcanist", "Herald of the Tome", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("arcanist", "Soldier of Apocrypha", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("arcanist", "Curative Runeforms", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("dragonknight", "Ardent Flame", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("dragonknight", "Draconic Power", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("dragonknight", "Earthen Heart", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("necromancer", "Grave Lord", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("necromancer", "Bone Tyrant", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry(
            "necromancer",
            "Living Death",
            PARTIAL,
            True,
            UNREVIEWED,
            True,
            "ExtremeNecromancerLivingDeathHealingService",
            "Curative Curse has an implemented Extreme healing hook, but the full Living Death passive family has not yet been exhaustively reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry("nightblade", "Assassination", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("nightblade", "Shadow", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry(
            "nightblade",
            "Siphoning",
            PARTIAL,
            True,
            UNREVIEWED,
            True,
            "ExtremeNightbladeSiphoningHealingService",
            "Soul Siphoner has an implemented Extreme healing hook, but the full Siphoning passive family has not yet been exhaustively reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry("sorcerer", "Daedric Summoning", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("sorcerer", "Dark Magic", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("sorcerer", "Storm Calling", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("templar", "Aedric Spear", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("templar", "Dawn's Wrath", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("templar", "Restoring Light", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry("warden", "Animal Companions", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
        ExtremeHealingClassPassiveCoverageEntry(
            "warden",
            "Green Balance",
            PARTIAL,
            True,
            UNREVIEWED,
            True,
            "ExtremeWardenGreenBalanceHealingService",
            "Emerald Moss has an implemented Extreme healing hook, but the full Green Balance passive family has not yet been exhaustively reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry("warden", "Winter's Embrace", UNREVIEWED, None, UNREVIEWED, False, _NO_REVIEW_EVIDENCE, _NO_REVIEW_DETAIL),
    )

    @staticmethod
    def _canonical_families() -> tuple[tuple[str, str], ...]:
        return tuple(
            (eso_class, skill_line)
            for eso_class, skill_lines in CLASS_SKILL_LINES.items()
            for skill_line in skill_lines
        )

    def items(self) -> tuple[ExtremeHealingClassPassiveCoverageEntry, ...]:
        rows = self._ENTRIES
        self._validate(rows)
        return rows

    def summary(self) -> ExtremeHealingClassPassiveCoverageSummary:
        rows = self.items()
        reviewed = tuple(row for row in rows if row.review_status == REVIEWED)
        partial = tuple(row for row in rows if row.review_status == PARTIAL)
        known_relevant = tuple(row for row in rows if row.healing_relevant is True)
        reviewed_relevant = tuple(row for row in reviewed if row.healing_relevant is True)
        return ExtremeHealingClassPassiveCoverageSummary(
            total_families=len(rows),
            reviewed_families=len(reviewed),
            partially_reviewed_families=len(partial),
            unreviewed_families=sum(row.review_status == UNREVIEWED for row in rows),
            healing_relevant_families=len(known_relevant),
            implemented=sum(row.coverage_status == IMPLEMENTED for row in reviewed_relevant),
            explicitly_unsupported=sum(
                row.coverage_status == EXPLICITLY_UNSUPPORTED for row in reviewed_relevant
            ),
            healing_relevant_unreviewed=sum(
                row.coverage_status == UNREVIEWED for row in known_relevant
            ),
            implemented_hooks=sum(row.implemented_hook for row in rows),
        )

    def _validate(
        self,
        rows: tuple[ExtremeHealingClassPassiveCoverageEntry, ...],
    ) -> None:
        canonical = self._canonical_families()
        actual = tuple((row.eso_class, row.skill_line) for row in rows)
        if len(actual) != len(set(actual)):
            raise ValueError("Extreme healer class-passive inventory contains duplicate families")

        missing = tuple(family for family in canonical if family not in actual)
        extra = tuple(family for family in actual if family not in canonical)
        if missing or extra:
            raise ValueError(
                "Extreme healer class-passive inventory must exactly match canonical class skill lines; "
                f"missing={missing}, extra={extra}"
            )

        for row in rows:
            if row.review_status not in {REVIEWED, PARTIAL, UNREVIEWED}:
                raise ValueError(
                    f"Invalid class-passive review status for {row.family_id}: {row.review_status}"
                )
            if row.review_status == UNREVIEWED:
                if row.healing_relevant is not None or row.coverage_status != UNREVIEWED:
                    raise ValueError(
                        f"Unreviewed class-passive family must remain unresolved: {row.family_id}"
                    )
                if row.implemented_hook:
                    raise ValueError(
                        f"Implemented hook requires at least partial family review: {row.family_id}"
                    )
                continue
            if row.healing_relevant is None:
                raise ValueError(
                    f"Reviewed or partial class-passive family must declare healing relevance: {row.family_id}"
                )
            if row.review_status == PARTIAL:
                if row.healing_relevant is not True or row.coverage_status != UNREVIEWED:
                    raise ValueError(
                        f"Partial family review must remain healing-relevant and unresolved: {row.family_id}"
                    )
                continue
            if row.healing_relevant is False:
                if row.coverage_status != NOT_APPLICABLE:
                    raise ValueError(
                        f"Reviewed non-healing family must be not_applicable: {row.family_id}"
                    )
                continue
            if row.coverage_status not in {
                IMPLEMENTED,
                EXPLICITLY_UNSUPPORTED,
                UNREVIEWED,
            }:
                raise ValueError(
                    f"Healing-relevant class-passive family has invalid coverage status: {row.family_id}"
                )
