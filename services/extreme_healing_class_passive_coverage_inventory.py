from __future__ import annotations

from dataclasses import dataclass

from minmax.passive_eligibility import CLASS_SKILL_LINES


REVIEWED = "reviewed"
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
    evidence: str
    detail: str

    @property
    def family_id(self) -> str:
        return f"{self.eso_class}:{self.skill_line}"


@dataclass(frozen=True)
class ExtremeHealingClassPassiveCoverageSummary:
    total_families: int
    reviewed_families: int
    unreviewed_families: int
    healing_relevant_families: int
    implemented: int
    explicitly_unsupported: int
    healing_relevant_unreviewed: int

    @property
    def complete(self) -> bool:
        return (
            self.unreviewed_families == 0
            and self.explicitly_unsupported == 0
            and self.healing_relevant_unreviewed == 0
        )


class ExtremeHealingClassPassiveCoverageInventory:
    """Canonical review denominator for healing-relevant class passive families.

    Every class skill-line family in ``CLASS_SKILL_LINES`` must appear exactly
    once. A family remains ``unreviewed`` until Extreme has deliberately decided
    whether its passives can change the actual-heal objective. Reviewed families
    that are healing-relevant then declare whether that behavior is implemented,
    explicitly unsupported, or still unreviewed.

    The inventory intentionally starts conservative. Existing dedicated Extreme
    healer services are evidence for the three currently reviewed families; the
    remaining canonical class families stay visible as unresolved review work.
    """

    _ENTRIES = (
        ExtremeHealingClassPassiveCoverageEntry(
            "arcanist",
            "Herald of the Tome",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "arcanist",
            "Soldier of Apocrypha",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "arcanist",
            "Curative Runeforms",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "dragonknight",
            "Ardent Flame",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "dragonknight",
            "Draconic Power",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "dragonknight",
            "Earthen Heart",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "necromancer",
            "Grave Lord",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "necromancer",
            "Bone Tyrant",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "necromancer",
            "Living Death",
            REVIEWED,
            True,
            IMPLEMENTED,
            "ExtremeNecromancerLivingDeathHealingService",
            "Reviewed Living Death healing-passive behavior is modeled with explicit condition evidence.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "nightblade",
            "Assassination",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "nightblade",
            "Shadow",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "nightblade",
            "Siphoning",
            REVIEWED,
            True,
            IMPLEMENTED,
            "ExtremeNightbladeSiphoningHealingService",
            "Reviewed Siphoning healing-passive behavior is modeled from active-bar and passive-rank evidence.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "sorcerer",
            "Daedric Summoning",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "sorcerer",
            "Dark Magic",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "sorcerer",
            "Storm Calling",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "templar",
            "Aedric Spear",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "templar",
            "Dawn's Wrath",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "templar",
            "Restoring Light",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "warden",
            "Animal Companions",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "warden",
            "Green Balance",
            REVIEWED,
            True,
            IMPLEMENTED,
            "ExtremeWardenGreenBalanceHealingService",
            "Reviewed Green Balance healing-passive behavior is modeled from active-bar and passive-rank evidence.",
        ),
        ExtremeHealingClassPassiveCoverageEntry(
            "warden",
            "Winter's Embrace",
            UNREVIEWED,
            None,
            UNREVIEWED,
            "No completed Extreme healer class-passive review recorded",
            "Class-passive relevance to MOST Actual Heal has not yet been reviewed.",
        ),
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
        relevant = tuple(row for row in reviewed if row.healing_relevant is True)
        return ExtremeHealingClassPassiveCoverageSummary(
            total_families=len(rows),
            reviewed_families=len(reviewed),
            unreviewed_families=sum(row.review_status == UNREVIEWED for row in rows),
            healing_relevant_families=len(relevant),
            implemented=sum(row.coverage_status == IMPLEMENTED for row in relevant),
            explicitly_unsupported=sum(
                row.coverage_status == EXPLICITLY_UNSUPPORTED for row in relevant
            ),
            healing_relevant_unreviewed=sum(
                row.coverage_status == UNREVIEWED for row in relevant
            ),
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
            if row.review_status not in {REVIEWED, UNREVIEWED}:
                raise ValueError(
                    f"Invalid class-passive review status for {row.family_id}: {row.review_status}"
                )
            if row.review_status == UNREVIEWED:
                if row.healing_relevant is not None or row.coverage_status != UNREVIEWED:
                    raise ValueError(
                        f"Unreviewed class-passive family must remain unresolved: {row.family_id}"
                    )
                continue
            if row.healing_relevant is None:
                raise ValueError(
                    f"Reviewed class-passive family must declare healing relevance: {row.family_id}"
                )
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
