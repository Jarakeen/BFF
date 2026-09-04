from __future__ import annotations

"""Data-driven in-app help content for FoundryDock.

The same topic records can later feed contextual help buttons, onboarding, and
other guidance surfaces without duplicating explanations across the UI.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class HelpSection:
    title: str
    body: str


@dataclass(frozen=True)
class HelpTopic:
    key: str
    title: str
    summary: str
    sections: tuple[HelpSection, ...]
    related: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


HELP_TOPICS: tuple[HelpTopic, ...] = (
    HelpTopic(
        key="getting_started",
        title="Getting Started",
        summary="The shortest path from an empty app to a usable ESO raid workspace.",
        sections=(
            HelpSection(
                "A sensible first pass",
                "Add or review your characters and builds, add people to the Roster, assign team names, then use Comp Builder or Optimization when you want BFF to help assemble a raid plan.",
            ),
            HelpSection(
                "How BFF treats data",
                "BFF keeps source-backed game data, reviewed encounter facts, calculated recommendations, and user-entered strategy separate. If a fact is unresolved, the app should say so instead of quietly inventing an answer.",
            ),
            HelpSection(
                "Where to look",
                "Builds describes individual saved builds. Roster describes people and teams. Comp Builder assembles a team. Optimization compares candidates under constraints. Mechanics explains encounters. Reference Data is a quick combat dictionary.",
            ),
        ),
        related=("builds", "roster", "comp_builder", "optimization", "mechanics"),
        keywords=("start", "first run", "new user", "workflow"),
    ),
    HelpTopic(
        key="builds",
        title="Builds",
        summary="Create and save character builds once, then reuse them throughout BFF.",
        sections=(
            HelpSection(
                "What belongs here",
                "A build is a saved combat configuration for a character: gear, weapons, skills, attributes, Mundus, consumables, Champion Points, notes, and encounter variants where available.",
            ),
            HelpSection(
                "Character versus build",
                "The character is the persistent identity. Builds are separate configurations that belong to that character. One healer can therefore keep DF Healer, GH Healer, and other encounter-specific builds without recreating the person each time.",
            ),
            HelpSection(
                "Sharing",
                "Export / Share creates a themed PDF for people. CSV remains the practical machine-readable export for backups and interchange.",
            ),
        ),
        related=("roster", "comp_builder", "optimization", "exports"),
        keywords=("gear", "skills", "character", "loadout", "pdf", "csv"),
    ),
    HelpTopic(
        key="roster",
        title="Roster & Teams",
        summary="Track people, characters, roles, team membership, raid schedules, and assignments.",
        sections=(
            HelpSection(
                "Roster records",
                "Roster is about people and their raid identities. It does not replace saved Builds. A person can have multiple builds and can belong to more than one team.",
            ),
            HelpSection(
                "Raid times",
                "Team Schedule stores recurring raid days, start time, and an explicit IANA time zone such as America/New_York or Europe/London. Full time-zone names avoid the ambiguity of abbreviations and survive daylight-saving changes more reliably.",
            ),
            HelpSection(
                "Assignments",
                "Generated or optimized teams can be sent to Roster as assignment plans. BFF preserves personnel records rather than silently rewriting people to match a generated comp.",
            ),
        ),
        related=("builds", "comp_builder", "optimization", "exports"),
        keywords=("team", "schedule", "timezone", "assignment", "raid time", "days"),
    ),
    HelpTopic(
        key="comp_builder",
        title="Comp Builder",
        summary="Build a raid team from saved players, generated recruits, and explicit constraints.",
        sections=(
            HelpSection(
                "What Generate Team does",
                "Comp Builder fills raid slots while respecting role requirements, saved-player anchors, encounter needs, provider coverage, and any supported forced build or gear constraints.",
            ),
            HelpSection(
                "Anchors and recruits",
                "Anchored players remain fixed while BFF fills open chairs. A recruitment slot is an explicit missing requirement, not a fabricated person.",
            ),
            HelpSection(
                "Why this team",
                "The useful answer is not only who was selected, but why. Coverage and responsibility data explain which player or build is expected to provide important raid effects and duties.",
            ),
        ),
        related=("roster", "optimization", "coverage", "builds"),
        keywords=("generate team", "anchor", "recruit", "forced gear", "provider"),
    ),
    HelpTopic(
        key="optimization",
        title="Optimization",
        summary="Compare candidate changes under explicit damage, sustain, role, and encounter constraints.",
        sections=(
            HelpSection(
                "What BFF is optimizing",
                "Optimization evaluates defined candidate changes against the selected evaluation context. A higher raw damage result is not automatically a valid recommendation if it breaks sustain, role boundaries, required coverage, or encounter constraints.",
            ),
            HelpSection(
                "Rejected candidates",
                "A rejected candidate can still show a useful damage increase. The rejection reason tells you which hard requirement it failed. This is intentional: BFF should show the tempting bad answer instead of hiding why it was rejected.",
            ),
            HelpSection(
                "Role boundaries",
                "Healer, tank, and damage roles are not interchangeable simply because one statistic improves. Diagnostic overrides may let you inspect a mismatch, but that does not turn the mismatch into a recommendation.",
            ),
        ),
        related=("builds", "comp_builder", "coverage"),
        keywords=("candidate", "sustain", "damage", "constraints", "ranking", "rejected"),
    ),
    HelpTopic(
        key="coverage",
        title="Coverage",
        summary="See which players and builds provide the buffs, debuffs, and responsibilities a team needs.",
        sections=(
            HelpSection(
                "Coverage is ownership",
                "Coverage answers who is responsible for providing a required effect or duty. It is different from merely proving that an effect exists somewhere in the game data.",
            ),
            HelpSection(
                "Missing coverage",
                "A missing provider should remain visibly missing. BFF should not silently assign an unsupported source or pretend a role can provide something it cannot.",
            ),
        ),
        related=("comp_builder", "optimization", "roster"),
        keywords=("buff", "debuff", "provider", "responsibility", "missing"),
    ),
    HelpTopic(
        key="mechanics",
        title="Mechanics / Boss Guide",
        summary="Search and inspect source-backed boss abilities, phases, reviewed mechanics, maps, and encounter facts.",
        sections=(
            HelpSection(
                "What the tabs mean",
                "Named Abilities come from persisted encounter source records. Thresholds and timeline entries come from explicit structural or reviewed canonical facts. Strategy and assignments remain separate evidence domains until they are explicitly supported.",
            ),
            HelpSection(
                "Search Boss Mechs",
                "The search box can match boss names, content names, locations, summaries, ability names and descriptions, interrupt notes, phase text, and reviewed canonical mechanic text. Content filtering can narrow the search to one dungeon, trial, or arena.",
            ),
            HelpSection(
                "Unresolved means unresolved",
                "Blank health, timing, strategy, or mechanic fields are displayed as unresolved when BFF does not have trustworthy persisted data. That is preferable to a confident guess made five minutes before pull.",
            ),
        ),
        related=("reference_data", "coverage"),
        keywords=("boss", "ability", "phase", "search", "raid map", "canonical", "mechanic"),
    ),
    HelpTopic(
        key="timers",
        title="Timers",
        summary="Operate encounter timers with large, raid-friendly controls and explicit manual state.",
        sections=(
            HelpSection(
                "Console-style operation",
                "Timer pages are designed for use while actively playing. Large controls and compact status displays favor fast manual input over dense planning UI.",
            ),
            HelpSection(
                "Manual truth",
                "Unless a future telemetry source is explicitly connected, timer buttons and user-entered events are the source of truth. BFF does not pretend it can see your Xbox combat state.",
            ),
        ),
        related=("mechanics",),
        keywords=("asylum", "perfecta", "console mode", "timer", "manual"),
    ),
    HelpTopic(
        key="reference_data",
        title="Reference Data",
        summary="Use the quick combat dictionary when you need a fast definition rather than a full boss guide.",
        sections=(
            HelpSection(
                "Reference versus Mechanics",
                "Reference Data is for general combat concepts, attacks, effects, and quick explanations. Boss-specific encounter research belongs in Mechanics, where it can retain encounter identity and provenance.",
            ),
        ),
        related=("mechanics",),
        keywords=("dictionary", "status effect", "attack", "lookup"),
    ),
    HelpTopic(
        key="exports",
        title="Exports & Sharing",
        summary="Share readable raid information without sacrificing machine-readable data.",
        sections=(
            HelpSection(
                "Share PDF",
                "Human-facing PDFs use the active Black Feather Foundry or Rylo visual theme. Builds are exported as dossiers; rosters include assignments and team schedules where available.",
            ),
            HelpSection(
                "CSV and structured data",
                "CSV and similar structured formats stay visually neutral because their job is interchange and backup, not impressing Discord with tasteful borders.",
            ),
        ),
        related=("builds", "roster"),
        keywords=("pdf", "csv", "share", "foundry", "rylo", "template"),
    ),
    HelpTopic(
        key="settings",
        title="Settings & Themes",
        summary="Control application preferences, visual theme, accessibility, optional modules, and data-management tools.",
        sections=(
            HelpSection(
                "Visual themes",
                "Foundry and Rylo change presentation, not game logic. Theme-aware exports use the active visual identity while preserving the same underlying build and roster data.",
            ),
            HelpSection(
                "Optional modules",
                "Features such as Broadcast can be excluded or hidden without changing the Raid Engine data model. Settings remains the stable place for application-level controls.",
            ),
        ),
        related=("exports", "troubleshooting"),
        keywords=("theme", "rylo", "foundry", "broadcast", "accessibility"),
    ),
    HelpTopic(
        key="troubleshooting",
        title="Troubleshooting",
        summary="A few useful checks before declaring the app haunted.",
        sections=(
            HelpSection(
                "Data looks wrong",
                "First determine whether the problem is presentation, persisted canonical data, or raw source data. BFF intentionally keeps those layers separate so a bad source record can be corrected without rewriting unrelated mechanics.",
            ),
            HelpSection(
                "A page says unresolved",
                "Unresolved is a data state, not necessarily an application error. If a value should exist, use the encounter or data-management tools to inspect whether the source was imported and reviewed.",
            ),
            HelpSection(
                "After updating",
                "Pull the current branch, restart the app when UI install layers changed, and run the focused pytest command supplied with the change before assuming a regression is real.",
            ),
        ),
        related=("getting_started", "mechanics", "settings"),
        keywords=("error", "bug", "unresolved", "restart", "pytest", "data"),
    ),
)


_TOPIC_BY_KEY = {topic.key: topic for topic in HELP_TOPICS}


def help_topic(key: str) -> HelpTopic | None:
    return _TOPIC_BY_KEY.get(str(key or "").strip())


def search_help_topics(query: str) -> tuple[HelpTopic, ...]:
    text = str(query or "").strip().casefold()
    if not text:
        return HELP_TOPICS

    matches: list[HelpTopic] = []
    for topic in HELP_TOPICS:
        haystack = " ".join(
            [
                topic.title,
                topic.summary,
                *topic.keywords,
                *(section.title for section in topic.sections),
                *(section.body for section in topic.sections),
            ]
        ).casefold()
        if text in haystack:
            matches.append(topic)
    return tuple(matches)
