from __future__ import annotations

from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus


def constraint_plain_english(constraint: CandidateConstraint) -> str:
    """Translate one Phase 12 hard-constraint result into user-facing language.

    This is deliberately presentation-only. The technical constraint status and
    explanation remain authoritative for ranking and audit evidence.
    """

    name = str(constraint.name or "").strip().casefold()
    status = constraint.status

    if "sustain" in name:
        if status is ConstraintStatus.REPAIRED:
            return "This change fixes the resource problem in the current build."
        if status is ConstraintStatus.IMPROVED:
            return "This change improves resource sustain compared with the current build."
        if status is ConstraintStatus.PRESERVED:
            return "This change keeps resource sustain at least as safe as the current build."
        if status is ConstraintStatus.UNSATISFIED:
            return "This setup still runs out of the required resource, so it cannot be recommended."
        if status is ConstraintStatus.WORSENED:
            return "This change makes resource sustain worse, so it is blocked."
        if status is ConstraintStatus.UNKNOWN:
            return "BFF cannot prove that this setup can sustain its resource use, so it will not guess."

    if "capability" in name or "coverage" in name:
        if status is ConstraintStatus.REPAIRED:
            return "This change restores a useful build capability that the current setup is missing."
        if status is ConstraintStatus.IMPROVED:
            return "This change adds useful build capability without removing the current coverage."
        if status is ConstraintStatus.PRESERVED:
            return "This change keeps the buffs, debuffs, and other resolved capabilities the current build provides."
        if status in {ConstraintStatus.WORSENED, ConstraintStatus.UNSATISFIED}:
            return "This change removes required build capability, so it is blocked."
        if status is ConstraintStatus.UNKNOWN:
            return "BFF cannot prove that the build still provides its required capabilities, so it will not guess."

    if "provider" in name or "responsibility" in name:
        if status is ConstraintStatus.PRESERVED:
            return "This change keeps the raid jobs assigned to this character."
        if status is ConstraintStatus.IMPROVED:
            return "This change keeps the current raid jobs and improves provider coverage."
        if status is ConstraintStatus.REPAIRED:
            return "This change restores an assigned raid responsibility that was not being met."
        if status in {ConstraintStatus.WORSENED, ConstraintStatus.UNSATISFIED}:
            return "This change would stop the character from reliably doing an assigned raid job, so it is blocked."
        if status is ConstraintStatus.UNKNOWN:
            return "BFF cannot prove that the character can still handle the assigned raid job, so it will not guess."

    if status is ConstraintStatus.REPAIRED:
        return "This change fixes a hard requirement that the current build fails."
    if status is ConstraintStatus.IMPROVED:
        return "This change improves this requirement compared with the current build."
    if status is ConstraintStatus.PRESERVED:
        return "This requirement remains safely satisfied."
    if status in {ConstraintStatus.WORSENED, ConstraintStatus.UNSATISFIED}:
        return "This change fails a required check, so it cannot be recommended."
    if status is ConstraintStatus.UNKNOWN:
        return "BFF does not have enough evidence to prove this requirement is satisfied, so it will not guess."

    return "BFF recorded this requirement result, but no plain-English summary is available yet."


def recommendation_reason_plain_english(*, is_constraint_repair: bool, delta: float | None) -> str:
    if is_constraint_repair:
        if delta is not None and delta > 0:
            return "This option fixes a required problem in the current build and also improves the modeled result."
        return "This option is recommended because it fixes a required problem in the current build, even without a higher modeled score."
    if delta is not None and delta > 0:
        return "This option passes the required checks and improves the modeled result."
    return "This option passes the required checks and is the best eligible result in this comparison."
