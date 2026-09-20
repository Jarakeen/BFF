from discord_companion.formatting import (
    format_build_brief,
    format_raid_brief,
    split_discord_message,
)
from services.discord_companion_service import DiscordBuildBrief, DiscordRaidBrief, DiscordRaidMemberBrief


def test_format_build_brief_includes_planned_state() -> None:
    brief = DiscordBuildBrief(
        plan_id="plan-1",
        plan_name="Swashbuckler",
        seat_id="healer-1",
        player="Jarakeen",
        character="Magrat",
        role="Healer",
        eso_class="Warden",
        build="RoJo",
        gear_sets=("Roaring Opportunist", "Jorvuld's Guidance"),
        skills=("Budding Seeds", "Combat Prayer"),
        mundus="The Thief",
        assignments=("Major Slayer",),
        notes="Kite.",
    )
    text = format_build_brief(brief)
    assert "Jarakeen" in text
    assert "Roaring Opportunist" in text
    assert "Major Slayer" in text


def test_format_raid_brief_keeps_open_recruitment_visible() -> None:
    brief = DiscordRaidBrief(
        plan_id="plan-1",
        name="Swashbuckler",
        trial_id="dreadsail_reef",
        difficulty="Veteran Hard Mode",
        team_name="Performance Mode",
        plan_note="Bring repair kits.",
        members=(
            DiscordRaidMemberBrief(
                seat_id="dd-8",
                player="Recruitment Needed",
                role="DD",
                eso_class="",
                build="",
                gear_sets=(),
                assignments=(),
                notes="",
            ),
        ),
    )
    text = format_raid_brief(brief)
    assert "Recruitment Needed" in text
    assert "Performance Mode" in text


def test_split_discord_message_respects_limit() -> None:
    chunks = split_discord_message("\n".join("x" * 80 for _ in range(80)), limit=500)
    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)
