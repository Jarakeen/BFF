from __future__ import annotations

from services.discord_profile_screenshot_intake_service import parse_discord_profile_text


def test_parse_discord_profile_text_extracts_explicit_profile_fields() -> None:
    result = parse_discord_profile_text(
        """
        Raven Keen
        @jarakeen
        About Me
        Xbox
        Jarakeen
        Connections
        Twitch
        https://twitch.tv/jarakeen
        YouTube
        https://youtube.com/@jarakeenESO
        """
    )

    assert result.discord == "@jarakeen"
    assert result.xbox == "Jarakeen"
    assert result.twitch == "jarakeen"
    assert result.youtube == "jarakeenESO"
    assert result.warnings == ()


def test_parse_discord_profile_text_accepts_inline_labels() -> None:
    result = parse_discord_profile_text(
        """
        Username: keen.raven
        Xbox Gamertag: KeenOnXbox
        Twitch: keen_streams
        YouTube: KeenESO
        """
    )

    assert result.discord == "keen.raven"
    assert result.xbox == "KeenOnXbox"
    assert result.twitch == "keen_streams"
    assert result.youtube == "KeenESO"


def test_parse_discord_profile_text_uses_display_name_fallback_only_when_needed() -> None:
    result = parse_discord_profile_text(
        """
        User Profile
        Raven Keen
        Member Since
        Sep 2020
        """
    )

    assert result.discord == "Raven Keen"
    assert result.xbox == ""
    assert result.youtube == ""
    assert result.twitch == ""


def test_parse_discord_profile_text_reports_unrecognized_profile_text() -> None:
    result = parse_discord_profile_text("User Profile\nAbout Me\nConnections")

    assert result.discord == ""
    assert result.warnings
