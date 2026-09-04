from services.help_topics import HELP_TOPICS, help_topic, search_help_topics


def test_core_help_topics_are_available() -> None:
    keys = {topic.key for topic in HELP_TOPICS}
    assert {
        "getting_started",
        "builds",
        "roster",
        "comp_builder",
        "optimization",
        "coverage",
        "mechanics",
        "timers",
        "reference_data",
        "exports",
        "settings",
        "troubleshooting",
    } <= keys


def test_help_search_matches_body_and_keywords() -> None:
    sustain = {topic.key for topic in search_help_topics("sustain")}
    timezone = {topic.key for topic in search_help_topics("timezone")}
    canonical = {topic.key for topic in search_help_topics("canonical")}

    assert "optimization" in sustain
    assert "roster" in timezone
    assert "mechanics" in canonical


def test_blank_help_search_returns_full_catalog() -> None:
    assert search_help_topics("") == HELP_TOPICS


def test_help_topic_lookup_is_explicit() -> None:
    assert help_topic("builds").title == "Builds"
    assert help_topic("not-a-topic") is None
