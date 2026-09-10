from __future__ import annotations

from dataclasses import dataclass

from minmax.passive_eligibility import CLASS_SKILL_LINES
from services.extreme_arcanist_curative_runeforms_passive_review import ExtremeArcanistCurativeRuneformsPassiveReview
from services.extreme_arcanist_herald_of_the_tome_passive_review import ExtremeArcanistHeraldOfTheTomePassiveReview
from services.extreme_arcanist_soldier_of_apocrypha_passive_review import ExtremeArcanistSoldierOfApocryphaPassiveReview
from services.extreme_dragonknight_ardent_flame_passive_review import ExtremeDragonknightArdentFlamePassiveReview
from services.extreme_dragonknight_draconic_power_passive_review import ExtremeDragonknightDraconicPowerPassiveReview
from services.extreme_dragonknight_earthen_heart_passive_review import ExtremeDragonknightEarthenHeartPassiveReview
from services.extreme_necromancer_living_death_passive_review import ExtremeNecromancerLivingDeathPassiveReview
from services.extreme_nightblade_assassination_passive_review import ExtremeNightbladeAssassinationPassiveReview
from services.extreme_nightblade_shadow_passive_review import ExtremeNightbladeShadowPassiveReview
from services.extreme_nightblade_siphoning_passive_review import ExtremeNightbladeSiphoningPassiveReview
from services.extreme_sorcerer_daedric_summoning_passive_review import ExtremeSorcererDaedricSummoningPassiveReview
from services.extreme_sorcerer_dark_magic_passive_review import ExtremeSorcererDarkMagicPassiveReview
from services.extreme_sorcerer_storm_calling_passive_review import ExtremeSorcererStormCallingPassiveReview
from services.extreme_templar_aedric_spear_passive_review import ExtremeTemplarAedricSpearPassiveReview
from services.extreme_templar_dawns_wrath_passive_review import ExtremeTemplarDawnsWrathPassiveReview
from services.extreme_templar_restoring_light_passive_review import ExtremeTemplarRestoringLightPassiveReview
from services.extreme_warden_animal_companions_passive_review import ExtremeWardenAnimalCompanionsPassiveReview
from services.extreme_warden_green_balance_passive_review import ExtremeWardenGreenBalancePassiveReview
from services.extreme_warden_winters_embrace_passive_review import ExtremeWardenWintersEmbracePassiveReview

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
    """Canonical family-review denominator for Extreme MOST Actual Heal."""

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
    _NO_REVIEW_DETAIL = "Class-passive relevance to MOST Actual Heal has not yet been reviewed."

    @classmethod
    def _unreviewed(cls, eso_class: str, skill_line: str) -> ExtremeHealingClassPassiveCoverageEntry:
        return ExtremeHealingClassPassiveCoverageEntry(
            eso_class, skill_line, UNREVIEWED, None, UNREVIEWED, False,
            cls._NO_REVIEW_EVIDENCE, cls._NO_REVIEW_DETAIL,
        )

    @staticmethod
    def _reviewed(
        eso_class: str,
        skill_line: str,
        healing_relevant: bool,
        evidence: str,
        detail: str,
    ) -> ExtremeHealingClassPassiveCoverageEntry:
        return ExtremeHealingClassPassiveCoverageEntry(
            eso_class=eso_class,
            skill_line=skill_line,
            review_status=REVIEWED,
            healing_relevant=healing_relevant,
            coverage_status=IMPLEMENTED if healing_relevant else NOT_APPLICABLE,
            implemented_hook=healing_relevant,
            evidence=evidence,
            detail=detail,
        )

    def _entries(self) -> tuple[ExtremeHealingClassPassiveCoverageEntry, ...]:
        overrides = {
            ("arcanist", "Herald of the Tome"): self._reviewed(
                "arcanist", "Herald of the Tome", True,
                "ExtremeArcanistHeraldOfTheTomePassiveReview + Fated Fortune + Harnessed Quintessence canonical bridges",
                "Fated Fortune and Harnessed Quintessence are implemented with explicit runtime proof before canonical heal evaluation.",
            ),
            ("arcanist", "Soldier of Apocrypha"): self._reviewed(
                "arcanist", "Soldier of Apocrypha", False,
                "ExtremeArcanistSoldierOfApocryphaPassiveReview",
                "All live-U50 Soldier passives are reviewed and none enlarge one healing-event magnitude.",
            ),
            ("arcanist", "Curative Runeforms"): self._reviewed(
                "arcanist", "Curative Runeforms", True,
                "ExtremeArcanistCurativeRuneformsPassiveReview + ExtremeArcanistCurativeRuneformsHealingService",
                "Healing Tides is implemented through explicit active-Crux conditional orchestration.",
            ),
            ("dragonknight", "Ardent Flame"): self._reviewed(
                "dragonknight", "Ardent Flame", True,
                "ExtremeDragonknightArdentFlamePassiveReview + DragonknightPassiveInputResolver + BuildCalculationContextFactory",
                "A Soul Ablaze is rank-aware and contributes canonical Healing Taken before self-heal scoring.",
            ),
            ("dragonknight", "Draconic Power"): self._reviewed(
                "dragonknight", "Draconic Power", True,
                "ExtremeDragonknightDraconicPowerPassiveReview + ExtremeDragonknightElderDragonCombatStateService",
                "Elder Dragon uses an explicitly proven Minor Brutality window before coefficient evaluation.",
            ),
            ("dragonknight", "Earthen Heart"): self._reviewed(
                "dragonknight", "Earthen Heart", False,
                "ExtremeDragonknightEarthenHeartPassiveReview",
                "All current Earthen Heart passives are reviewed and none enlarge one healing-event magnitude.",
            ),
            ("necromancer", "Living Death"): self._reviewed(
                "necromancer", "Living Death", True,
                "ExtremeNecromancerLivingDeathPassiveReview + ExtremeNecromancerLivingDeathHealingService",
                "Curative Curse is implemented; the remaining Living Death passives are objective-irrelevant.",
            ),
            ("nightblade", "Assassination"): self._reviewed(
                "nightblade", "Assassination", False,
                "ExtremeNightbladeAssassinationPassiveReview",
                "Assassination changes crit chance, Critical Damage, or sustain, not critical-heal magnitude.",
            ),
            ("nightblade", "Shadow"): self._reviewed(
                "nightblade", "Shadow", True,
                "ExtremeNightbladeShadowPassiveReview + NightbladePassiveInputResolver + BuildCalculationContextFactory",
                "Dark Vigor contributes canonical Max Health from explicit active-bar Shadow ability count.",
            ),
            ("nightblade", "Siphoning"): self._reviewed(
                "nightblade", "Siphoning", True,
                "ExtremeNightbladeSiphoningPassiveReview + NightbladePassiveInputResolver + ExtremeNightbladeSiphoningHealingService",
                "Magicka Flood and Soul Siphoner are implemented; the remaining passives are objective-irrelevant.",
            ),
            ("sorcerer", "Daedric Summoning"): self._reviewed(
                "sorcerer", "Daedric Summoning", True,
                "ExtremeSorcererDaedricSummoningPassiveReview + SorcererPassiveInputResolver + ExtremeSorcererExpertSummonerPetContextService",
                "Expert Summoner standing resource bonuses and explicit permanent-pet Max Health branch are implemented canonically.",
            ),
            ("sorcerer", "Dark Magic"): self._reviewed(
                "sorcerer", "Dark Magic", True,
                "ExtremeSorcererDarkMagicPassiveReview + ExtremeSorcererBloodMagicService",
                "Blood Magic is implemented as a distinct self-heal/resource branch with explicit runtime state.",
            ),
            ("sorcerer", "Storm Calling"): self._reviewed(
                "sorcerer", "Storm Calling", True,
                "ExtremeSorcererStormCallingPassiveReview + SorcererPassiveInputResolver",
                "Expert Mage is implemented through the canonical Weapon/Spell Damage pipeline.",
            ),
            ("templar", "Aedric Spear"): self._reviewed(
                "templar", "Aedric Spear", True,
                "ExtremeTemplarAedricSpearPassiveReview + TemplarPassiveInputResolver + BuildCalculationContextFactory",
                "Balanced Warrior is implemented through canonical Weapon/Spell Damage percent buckets.",
            ),
            ("templar", "Dawn's Wrath"): self._reviewed(
                "templar", "Dawn's Wrath", True,
                "ExtremeTemplarDawnsWrathPassiveReview + ExtremeTemplarIlluminateCombatStateService",
                "Illuminate contributes canonical Minor Sorcery only through an explicitly proven active window.",
            ),
            ("templar", "Restoring Light"): self._reviewed(
                "templar", "Restoring Light", True,
                "ExtremeTemplarRestoringLightPassiveReview + ExtremeTemplarRestoringLightHealingService",
                "Mending and Sacred Ground are implemented with explicit target/runtime state.",
            ),
            ("warden", "Animal Companions"): self._reviewed(
                "warden", "Animal Companions", True,
                "ExtremeWardenAnimalCompanionsPassiveReview + ExtremeWardenBondWithNatureHealingEventService",
                "Bond with Nature is implemented as a separate caster self-heal from a proven effect-ended event.",
            ),
            ("warden", "Green Balance"): self._reviewed(
                "warden", "Green Balance", True,
                "ExtremeWardenGreenBalancePassiveReview + ExtremeWardenGreenBalanceHealingService",
                "Accelerated Growth and Emerald Moss are implemented canonically.",
            ),
            ("warden", "Winter's Embrace"): self._reviewed(
                "warden", "Winter's Embrace", False,
                "ExtremeWardenWintersEmbracePassiveReview + WardenPassiveInputResolver",
                "All live-U50 Winter's Embrace passives are reviewed and none enlarge one healing-event magnitude.",
            ),
        }
        return tuple(overrides.get(family, self._unreviewed(*family)) for family in self._DECLARED_FAMILIES)

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
            explicitly_unsupported=sum(row.coverage_status == EXPLICITLY_UNSUPPORTED for row in reviewed_relevant),
            healing_relevant_unreviewed=sum(row.coverage_status == UNREVIEWED for row in known_relevant),
            implemented_hooks=sum(row.implemented_hook for row in rows),
        )

    def _validate(self, rows: tuple[ExtremeHealingClassPassiveCoverageEntry, ...]) -> None:
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

        review_checks = {
            "arcanist:Herald of the Tome": ExtremeArcanistHeraldOfTheTomePassiveReview,
            "arcanist:Soldier of Apocrypha": ExtremeArcanistSoldierOfApocryphaPassiveReview,
            "arcanist:Curative Runeforms": ExtremeArcanistCurativeRuneformsPassiveReview,
            "dragonknight:Ardent Flame": ExtremeDragonknightArdentFlamePassiveReview,
            "dragonknight:Draconic Power": ExtremeDragonknightDraconicPowerPassiveReview,
            "dragonknight:Earthen Heart": ExtremeDragonknightEarthenHeartPassiveReview,
            "necromancer:Living Death": ExtremeNecromancerLivingDeathPassiveReview,
            "nightblade:Assassination": ExtremeNightbladeAssassinationPassiveReview,
            "nightblade:Shadow": ExtremeNightbladeShadowPassiveReview,
            "nightblade:Siphoning": ExtremeNightbladeSiphoningPassiveReview,
            "sorcerer:Daedric Summoning": ExtremeSorcererDaedricSummoningPassiveReview,
            "sorcerer:Dark Magic": ExtremeSorcererDarkMagicPassiveReview,
            "sorcerer:Storm Calling": ExtremeSorcererStormCallingPassiveReview,
            "templar:Aedric Spear": ExtremeTemplarAedricSpearPassiveReview,
            "templar:Dawn's Wrath": ExtremeTemplarDawnsWrathPassiveReview,
            "templar:Restoring Light": ExtremeTemplarRestoringLightPassiveReview,
            "warden:Animal Companions": ExtremeWardenAnimalCompanionsPassiveReview,
            "warden:Green Balance": ExtremeWardenGreenBalancePassiveReview,
            "warden:Winter's Embrace": ExtremeWardenWintersEmbracePassiveReview,
        }

        for row in rows:
            if row.review_status not in {REVIEWED, PARTIAL, UNREVIEWED}:
                raise ValueError(f"Invalid class-passive review status for {row.family_id}: {row.review_status}")
            if row.review_status == UNREVIEWED:
                if row.healing_relevant is not None or row.coverage_status != UNREVIEWED or row.implemented_hook:
                    raise ValueError(f"Unreviewed class-passive family must remain unresolved: {row.family_id}")
                continue
            if row.healing_relevant is None:
                raise ValueError(f"Reviewed or partial class-passive family must declare healing relevance: {row.family_id}")
            if row.review_status == PARTIAL:
                if row.healing_relevant is not True or row.coverage_status != UNREVIEWED:
                    raise ValueError(f"Partial family review must remain healing-relevant and unresolved: {row.family_id}")
                continue
            if row.healing_relevant is False:
                if row.coverage_status != NOT_APPLICABLE or row.implemented_hook:
                    raise ValueError(f"Reviewed non-healing family must be not_applicable without an implementation hook: {row.family_id}")
            elif row.coverage_status not in {IMPLEMENTED, EXPLICITLY_UNSUPPORTED, UNREVIEWED}:
                raise ValueError(f"Healing-relevant class-passive family has invalid coverage status: {row.family_id}")

            review_type = review_checks.get(row.family_id)
            if review_type is None:
                raise ValueError(f"Reviewed class-passive family lacks a passive-level review guard: {row.family_id}")
            if not review_type().complete:
                raise ValueError(f"{row.skill_line} cannot be reviewed until its passive-level review is complete")
