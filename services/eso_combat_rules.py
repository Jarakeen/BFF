from __future__ import annotations

"""Small sourced ESO-wide combat rules used by encounter evaluation.

These are game-level rules, not encounter facts. Encounter-specific evidence may
override them. Keeping them separate avoids duplicating the same universal combat
mechanic into every boss evidence packet.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EsoCombatRule:
    rule_id: str
    statement: str
    source_name: str
    source_url: str
    source_note: str


STANDARD_INTERRUPT = EsoCombatRule(
    rule_id="standard_interrupt_core_bash",
    statement=(
        "An enemy action identified by the standard interrupt cue can be interrupted "
        "with the core bash/interrupt input at melee range unless encounter-specific "
        "evidence establishes an exception."
    ),
    source_name="The Elder Scrolls Online New Player Guide",
    source_url=(
        "https://forums.elderscrollsonline.com/en/discussion/60795/"
        "the-elder-scrolls-online-new-player-guide"
    ),
    source_note=(
        "Official ESO forum guide: glowing red enemy attacks are interruptible and the "
        "documented standard interrupt input is the block-plus-attack bash action."
    ),
)
