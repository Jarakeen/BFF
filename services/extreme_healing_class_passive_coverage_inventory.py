from __future__ import annotations

from dataclasses import dataclass

from minmax.passive_eligibility import CLASS_SKILL_LINES
from services.extreme_necromancer_living_death_passive_review import (
    ExtremeNecromancerLivingDeathPassiveReview,
)
from services.extreme_nightblade_siphoning_passive_review import (
    ExtremeNightbladeSiphoningPassiveReview,
)
from services.extreme_templar_restoring_light_passive_review import (
    ExtremeTemplarRestoringLightPassiveReview,
)
from services.extreme_warden_green_balance_passive_review import (
    ExtremeWardenGreenBalancePassiveReview,
)


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
    """Canonical family-review denominator for Extreme MOST Actual Heal.

    The explicit family declaration is intentionally duplicated against
    ``CLASS_SKILL_LINES``. That makes a newly-added canonical class family fail
    closed until Extreme deliberately adds and classifies it here.
    """

    _DECLARED_FAMILIES = (
        ("arcanist", "Herald of the Tome"),
        ("arcanist", "Soldier of Apocrypha"),
        ("arcanist", "Curative Runeforms"),
        ("dragonknight", "Ardent Flame"),
        ("dragonknight", "Draconic Power"),
        ("dragonknight", "Earthen Heart"),
        ("necromancer", "Grave Lord"),
        ("necromancer", "Bone Tyrant"),
        ("necromancer", "Living Death"),
        ("nightblade", "Assassination"),
        ("nightblade", "Shadow"),
        ("nightblade", "Siphoning"),
        ("sorcerer", "Daedric Summoning"),
        ("sorcerer", "Dark Magic"),
        ("sorcerer", "Storm Calling"),
        ("templar", "Aedric Spear"),
        ("templar", "Dawn's Wrath"),
        ("templar", "Restoring Light"),
        ("warden", "Animal Companions"),
        ("warden", "Green Balance"),
        ("warden", "Winter's Embrace"),
    )
    _NO_REVIEW_EVIDENCE = "No completed Extreme healer class-passive review recorded"
    _NO_REVIEW_DETAIL = (
        "Class-passive relevance to MOST Actual Heal has not yet been reviewed."
    )

    @classmethod
    def _unreviewed(
        cls,
        eso_class: str,
        skill_line: str,
    ) -> ExtremeHealingClassPassiveCoverageEntry:
        return ExtremeHealingClassPassiveCoverageEntry(
            eso_class,
            skill_line,
            UNREVIEWED,
            None,
            UNREVIEWED,
            False,
            cls._NO_REVIEW_EVIDENCE,
            cls._NO_REVIEW_DETAIL,
        )

    def _entries(self) -> tuple[ExtremeHealingClassPassiveCoverageEntry, ...]:
        overrides = {
            ("necromancer", "Living Death"): ExtremeHealingClassPassiveCoverageEntry(
                "necromancer",
                "Living Death",
                REVIEWED,
                True,
                IMPLEMENTED,
                True,
                "ExtremeNecromancerLivingDeathPassiveReview + ExtremeNecromancerLivingDeathHealingService",
                "All four Living Death passives are reviewed for MOST Actual Heal: Curative Curse is implemented; Near-Death Experience, Corpse Consumption, and Undead Confederate are objective-irrelevant.",
            ),
            ("nightblade", "Siphoning"): ExtremeHealingClassPassiveCoverageEntry(
                "nightblade",
                "Siphoning",
                REVIEWED,
                True,
                IMPLEMENTED,
                True,
                "ExtremeNightbladeSiphoningPassiveReview + NightbladePassiveInputResolver + ExtremeNightbladeSiphoningHealingService",
                "All four Siphoning passives are reviewed for MOST Actual Heal: Magicka Flood and Soul Siphoner are implemented; Catalyst and Transfer are objective-irrelevant.",
            ),
            ("templar", "Restoring Light"): ExtremeHealingClassPassiveCoverageEntry(
                "templar",
                "Restoring Light",
                REVIEWED,
                True,
                IMPLEMENTED,
                True,
                "ExtremeTemplarRestoringLightPassiveReview + ExtremeTemplarRestoringLightHealingService + ExtremeTemplarSacredGroundCombatStateService + ExtremeConditionalActualHealOptimizationService",
                "All four live-U50 Restoring Light passives are reviewed for MOST Actual Heal. Mending is applied by the conditional Actual Heal orchestration against explicit target Health; Sacred Ground contributes canonical Minor Mending through the combat-state path; Light Weaver and Master Ritualist are objective-irrelevant.",
            ),
            ("warden", "Green Balance"): ExtremeHealingClassPassiveCoverageEntry(
                "warden",
                "Green Balance",
                REVIEWED,
                True,
                IMPLEMENTED,
                True,
                "ExtremeWardenGreenBalancePassiveReview + ExtremeWardenGreenBalanceHealingService + ExtremeWardenAcceleratedGrowthCombatStateService",
                "All four Green Balance passives are reviewed for MOST Actual Heal: Accelerated Growth and Emerald Moss are implemented; Nature's Gift and Maturation are objective-irrelevant.",
            ),
        }
        return tuple(
            overrides.get(family, self._unreviewed(*family))
            for family in self._DECLARED_FAMILIES
        )

    @staticmethod
    def _canonical_families() -> tuple[tuple[str, str], ...]:
        return tuple(
            (eso_class, skill_line)
            for eso_class, skill_lines in CLASS_SKILL_LINES.items()
            for skill_line in skill_lines
        )

    def items(self) -> tuple[ExtremeHealingClassPassiveCoverageEntry, ...]:
        rows = self._entries()
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
        declared = self._DECLARED_FAMILIES
        actual = tuple((row.eso_class, row.skill_line) for row in rows)
        if len(declared) != len(set(declared)) or len(actual) != len(set(actual)):
            raise ValueError("Extreme healer class-passive inventory contains duplicate families")
        if declared != canonical or actual != canonical:
            missing = tuple(family for family in canonical if family not in declared)
            extra = tuple(family for family in declared if family not in canonical)
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
                if (
                    row.healing_relevant is not None
                    or row.coverage_status != UNREVIEWED
                    or row.implemented_hook
                ):
                    raise ValueError(
                        f"Unreviewed class-passive family must remain unresolved: {row.family_id}"
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
            if (
                row.family_id == "necromancer:Living Death"
                and not ExtremeNecromancerLivingDeathPassiveReview().complete
            ):
                raise ValueError(
                    "Living Death cannot be reviewed until its passive-level review is complete"
                )
            if (
                row.family_id == "nightblade:Siphoning"
                and not ExtremeNightbladeSiphoningPassiveReview().complete
            ):
                raise ValueError(
                    "Siphoning cannot be reviewed until its passive-level review is complete"
                )
            if (
                row.family_id == "templar:Restoring Light"
                and not ExtremeTemplarRestoringLightPassiveReview().complete
            ):
                raise ValueError(
                    "Restoring Light cannot be reviewed until its passive-level review is complete"
                )
            if (
                row.family_id == "warden:Green Balance"
                and not ExtremeWardenGreenBalancePassiveReview().complete
            ):
                raise ValueError(
                    "Green Balance cannot be reviewed until its passive-level review is complete"
                )
