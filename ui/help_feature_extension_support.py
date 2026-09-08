from __future__ import annotations

"""Add help content for newer convenience workflows without duplicating the base guide."""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    import services.help_topics as topics
    import ui.help_page as help_page

    extras = (
        topics.HelpTopic(
            key="screenshot_import",
            title="Import Builds from Screenshots",
            summary="Stage ESO Armory and Character Sheet screenshots so BFF can turn them into a reviewable build draft instead of making you hand-enter every character.",
            sections=(
                topics.HelpSection(
                    "Where to start",
                    "Open Builds and choose Import Screenshots. Add several Armory captures for the same build plus one matching Character Sheet capture. BFF keeps the whole set together as one pending import.",
                ),
                topics.HelpSection(
                    "Recommended captures",
                    "For the best draft, capture Armory Equipment / Attributes, Armory Skills, Armory Champion Points, and Character Sheet / Description. These views complement each other: equipment and bars live in Armory while character identity, race, class, alliance, and other persistent details live on the Character Sheet.",
                ),
                topics.HelpSection(
                    "Review before save",
                    "Screenshot import is review-first. BFF stages the evidence and later creates a draft; uncertain or conflicting fields must be confirmed before anything is written into builds.json. A blurry trait should remain uncertain rather than becoming a very confident lie.",
                ),
            ),
            related=("builds", "getting_started"),
            keywords=("screenshot", "camera", "armory", "character sheet", "import build", "photo", "xbox"),
        ),
        topics.HelpTopic(
            key="calendar_export",
            title="Add Raid Schedule to Calendar",
            summary="Turn a saved recurring Team Schedule into a portable .ics calendar event for Apple Calendar, Google Calendar, Outlook, and other compatible calendar apps.",
            sections=(
                topics.HelpSection(
                    "Save the team schedule first",
                    "Open Roster & Teams → Team Schedule and save the team's raid days, start time, and explicit time zone. The calendar event uses that stored schedule, so daylight-saving changes are handled by the named time zone instead of guesswork.",
                ),
                topics.HelpSection(
                    "Add to Calendar (.ics)",
                    "Choose Add to Calendar (.ics), save the calendar file, and BFF will ask the operating system to open it with your default calendar application. The event repeats weekly on the saved raid days.",
                ),
                topics.HelpSection(
                    "Why .ics",
                    ".ics is a portable calendar format, so the same export can be imported by Apple Calendar, Google Calendar, Outlook, and many phone calendar apps without BFF needing separate account logins or synchronization permissions.",
                ),
            ),
            related=("roster", "exports"),
            keywords=("calendar", "ics", "apple calendar", "google calendar", "outlook", "raid schedule", "recurring"),
        ),
    )

    existing = {topic.key for topic in topics.HELP_TOPICS}
    added = tuple(topic for topic in extras if topic.key not in existing)
    if not added:
        _INSTALLED = True
        return

    topics.HELP_TOPICS = topics.HELP_TOPICS + added
    topics._TOPIC_BY_KEY = {topic.key: topic for topic in topics.HELP_TOPICS}

    def help_topic(key: str):
        return topics._TOPIC_BY_KEY.get(str(key or "").strip())

    def search_help_topics(query: str):
        text = str(query or "").strip().casefold()
        if not text:
            return topics.HELP_TOPICS
        matches = []
        for topic in topics.HELP_TOPICS:
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

    topics.help_topic = help_topic
    topics.search_help_topics = search_help_topics

    # HelpPage imported these names directly, so refresh its bindings too.
    help_page.HELP_TOPICS = topics.HELP_TOPICS
    help_page.help_topic = help_topic
    help_page.search_help_topics = search_help_topics
    _INSTALLED = True
