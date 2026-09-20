from __future__ import annotations

"""Plain-text formatting helpers shared by Finch commands and tests."""

from services.discord_companion_service import (
    DiscordBuildBrief,
    DiscordRaidBrief,
    DiscordStrategyBrief,
)


DISCORD_MESSAGE_LIMIT = 2000


def _line(label: str, value: str) -> str:
    value = str(value or "").strip()
    return f"**{label}:** {value}" if value else ""


def format_raid_brief(brief: DiscordRaidBrief) -> str:
    heading = f"## {brief.name}"
    meta = " · ".join(
        value
        for value in (brief.trial_id, brief.difficulty, brief.team_name)
        if value
    )
    lines = [heading, meta]
    if brief.plan_note:
        lines.append(f"> {brief.plan_note}")

    for member in brief.members:
        identity = " · ".join(
            value
            for value in (member.player, member.role, member.eso_class)
            if value
        )
        detail = member.build or (" + ".join(member.gear_sets) if member.gear_sets else "")
        assignments = ", ".join(member.assignments)
        row = f"**{member.seat_id}** — {identity}"
        if detail:
            row += f"\n↳ {detail}"
        if assignments:
            row += f"\n↳ Assignments: {assignments}"
        lines.append(row)

    return "\n".join(line for line in lines if line).strip()


def format_build_brief(brief: DiscordBuildBrief) -> str:
    lines = [
        f"## {brief.player} · {brief.plan_name}",
        " · ".join(value for value in (brief.seat_id, brief.role, brief.eso_class) if value),
        _line("Character", brief.character),
        _line("Build", brief.build),
        _line("Gear", " + ".join(brief.gear_sets)),
        _line("Skills", ", ".join(brief.skills)),
        _line("Mundus", brief.mundus),
        _line("Assignments", ", ".join(brief.assignments)),
        _line("Notes", brief.notes),
    ]
    return "\n".join(line for line in lines if line).strip()


def format_strategy_brief(brief: DiscordStrategyBrief) -> str:
    lines = [f"## {brief.encounter_name or brief.encounter_id}"]
    if brief.callouts:
        lines.append("**Callouts**")
        lines.extend(f"• {row}" for row in brief.callouts[:6])

    if brief.strategy_rows:
        lines.append("**Strategy**")
        for mechanic, summary, mitigation in brief.strategy_rows[:8]:
            text = f"**{mechanic}:** {summary}"
            if mitigation:
                text += f"\n↳ {mitigation}"
            lines.append(text)

    if brief.role_impact:
        lines.append("**Role notes**")
        lines.extend(f"• {row}" for row in brief.role_impact[:6])

    if brief.timeline:
        lines.append("**Timeline**")
        for marker, label, detail in brief.timeline[:8]:
            lines.append(f"• **{marker} {label}:** {detail}")

    if len(lines) == 1:
        lines.append("No reviewed strategy material is stored for this encounter yet.")
    return "\n".join(lines).strip()


def split_discord_message(text: str, *, limit: int = DISCORD_MESSAGE_LIMIT) -> tuple[str, ...]:
    text = str(text or "").strip()
    if not text:
        return ("",)
    if len(text) <= limit:
        return (text,)

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in text.splitlines():
        needed = len(line) + (1 if current else 0)
        if current and current_len + needed > limit:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line)
            continue
        if len(line) > limit:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            for start in range(0, len(line), limit):
                chunks.append(line[start : start + limit])
            continue
        current.append(line)
        current_len += needed
    if current:
        chunks.append("\n".join(current))
    return tuple(chunks)


__all__ = [
    "DISCORD_MESSAGE_LIMIT",
    "format_build_brief",
    "format_raid_brief",
    "format_strategy_brief",
    "split_discord_message",
]
