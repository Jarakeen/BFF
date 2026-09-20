from __future__ import annotations

"""Finch Discord bot entry point."""

import discord
from discord import app_commands
from discord.ext import commands, tasks

from discord_companion.changes import BuildChangeMonitor
from discord_companion.config import DiscordCompanionConfig, load_config, write_example_config
from discord_companion.credentials import load_bot_token
from discord_companion.formatting import (
    format_raid_brief,
    format_strategy_brief,
    split_discord_message,
)
from discord_companion.registrations import FinchRegistrationStore
from discord_companion.reminders import RaidReminderService
from engine.config import get_data_dir
from services.discord_companion_service import (
    DiscordBuildBrief,
    FoundryDockDiscordCompanionService,
)
from services.eso_database import EsoDatabase
from services.raid_plan_repository import RaidPlanRepository
from services.roster_service import RosterService


FINCH_PURPLE = discord.Color.from_rgb(105, 84, 150)
FINCH_TEAL = discord.Color.from_rgb(89, 174, 179)
FINCH_GOLD = discord.Color.from_rgb(200, 164, 106)


def _companion() -> FoundryDockDiscordCompanionService:
    data_dir = get_data_dir()
    database = EsoDatabase(data_dir / "eso.db")
    roster = RosterService(database)
    return FoundryDockDiscordCompanionService(
        plan_repository=RaidPlanRepository(data_dir / "raid_plans.json"),
        roster_service=roster,
        data_dir=data_dir,
    )


def _trim(value: object, limit: int = 1024) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _bot_avatar_url(interaction: discord.Interaction) -> str | None:
    user = interaction.client.user
    if user is None:
        return None
    return str(user.display_avatar.url)


def _finch_embed(
    interaction: discord.Interaction,
    *,
    title: str,
    description: str = "",
    color: discord.Color = FINCH_PURPLE,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description or None,
        color=color,
    )
    avatar = _bot_avatar_url(interaction)
    if avatar:
        embed.set_thumbnail(url=avatar)
    embed.set_footer(text="Finch · FoundryDock Raid Companion")
    return embed


def _build_embed(
    interaction: discord.Interaction,
    brief: DiscordBuildBrief,
    *,
    compact: bool = False,
) -> discord.Embed:
    identity = " · ".join(
        part for part in (brief.seat_id, brief.role, brief.eso_class) if part
    )
    embed = _finch_embed(
        interaction,
        title=f"🐦‍⬛  {brief.player}",
        description=(
            f"**{brief.plan_name}**\n{identity}"
            if identity
            else f"**{brief.plan_name}**"
        ),
        color=FINCH_TEAL,
    )

    if brief.build:
        embed.add_field(name="⚒️ Build", value=_trim(brief.build), inline=False)

    if brief.gear_sets:
        gear = "\n".join(f"• {item}" for item in brief.gear_sets)
        embed.add_field(name="🛡️ Gear", value=_trim(gear), inline=False)

    if brief.assignments:
        assignments = "\n".join(f"• {item}" for item in brief.assignments)
        embed.add_field(
            name="📌 Assignments",
            value=_trim(assignments),
            inline=False,
        )

    if not compact and brief.skills:
        skills = " • ".join(brief.skills)
        embed.add_field(name="⚔️ Skills", value=_trim(skills), inline=False)

    if not compact and brief.mundus:
        embed.add_field(name="✦ Mundus", value=_trim(brief.mundus), inline=True)

    if not compact and brief.character:
        embed.add_field(
            name="Character",
            value=_trim(brief.character),
            inline=True,
        )

    if not compact and brief.notes:
        embed.add_field(
            name="📝 Field Notes",
            value=_trim(brief.notes),
            inline=False,
        )

    if compact:
        embed.set_footer(text="Use /build for full private build details · Finch")
    return embed


class FinchBot(commands.Bot):
    def __init__(self, config: DiscordCompanionConfig) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=discord.Intents.default(),
        )
        self.config = config
        self.foundry = _companion()
        self.reminders = RaidReminderService(
            roster_service=self.foundry.roster_service,
            config=config,
        )
        self.build_changes = BuildChangeMonitor(
            companion=self.foundry,
            config=config,
        )
        self.registrations = FinchRegistrationStore(
            path=get_data_dir() / "discord_registrations.json",
            roster_service=self.foundry.roster_service,
        )

    async def setup_hook(self) -> None:
        if self.config.guild_id:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        self.reminder_loop.start()
        self.build_change_loop.start()

    async def close(self) -> None:
        self.reminder_loop.cancel()
        self.build_change_loop.cancel()
        self.foundry.roster_service.db.close()
        await super().close()

    @tasks.loop(seconds=30)
    async def reminder_loop(self) -> None:
        for reminder in self.reminders.due_reminders():
            channel = self.get_channel(reminder.channel_id)
            if channel is None:
                try:
                    channel = await self.fetch_channel(reminder.channel_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    continue
            if not hasattr(channel, "send"):
                continue
            await channel.send(
                reminder.message,
                allowed_mentions=discord.AllowedMentions(
                    roles=True,
                    users=False,
                    everyone=False,
                ),
            )

    @reminder_loop.before_loop
    async def before_reminder_loop(self) -> None:
        await self.wait_until_ready()

    @tasks.loop(seconds=60)
    async def build_change_loop(self) -> None:
        for notice in self.build_changes.scan():
            channel = self.get_channel(notice.channel_id)
            if channel is None:
                try:
                    channel = await self.fetch_channel(notice.channel_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    continue
            if not hasattr(channel, "send"):
                continue
            await channel.send(notice.message)

    @build_change_loop.before_loop
    async def before_build_change_loop(self) -> None:
        await self.wait_until_ready()

    async def on_ready(self) -> None:
        await self.change_presence(
            activity=discord.Game(name="FoundryDock raid operations")
        )
        if not self.config.guild_id:
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
        if self.user is not None:
            guild_names = ", ".join(guild.name for guild in self.guilds) or "(no guilds)"
            print(
                f"Finch online as {self.user} (id={self.user.id}); "
                f"connected guilds: {guild_names}"
            )


bot: FinchBot | None = None


async def _respond(
    interaction: discord.Interaction,
    text: str,
    *,
    ephemeral: bool = True,
) -> None:
    chunks = split_discord_message(text)
    await interaction.response.send_message(chunks[0], ephemeral=ephemeral)
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk, ephemeral=ephemeral)


def _registration_for(interaction: discord.Interaction):
    assert bot is not None
    if interaction.guild_id is None:
        return None
    return bot.registrations.get(
        discord_user_id=interaction.user.id,
        guild_id=interaction.guild_id,
    )


def _registered_plan_ref(team_name: str) -> str:
    assert bot is not None
    plan = bot.foundry.active_plan_for_team(team_name)
    return plan.plan_id if plan is not None else ""


@app_commands.command(
    name="register",
    description="Link your Discord account to your FoundryDock team identity.",
)
@app_commands.describe(
    team="Your FoundryDock Team name.",
    player="Your FoundryDock Personnel player/gamertag.",
)
async def register(
    interaction: discord.Interaction,
    team: str,
    player: str,
) -> None:
    assert bot is not None
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "Registration must be completed inside a server where Finch is installed.",
            ephemeral=True,
        )
        return
    try:
        row = bot.registrations.register(
            discord_user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            team_name=team,
            player_ref=player,
        )
    except LookupError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    embed = _finch_embed(
        interaction,
        title="🐦‍⬛  Registration Complete",
        description=(
            f"**{row.player_name}** is now linked to your Discord account.\n"
            "Finch can use that identity for private raid information."
        ),
        color=FINCH_GOLD,
    )
    embed.add_field(name="Team", value=row.team_name, inline=True)
    embed.add_field(name="Next", value="Use **/me** for your raid brief.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(
    name="unregister",
    description="Remove your Discord-to-FoundryDock player link.",
)
async def unregister(interaction: discord.Interaction) -> None:
    assert bot is not None
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "Nothing to unregister here.",
            ephemeral=True,
        )
        return
    removed = bot.registrations.unregister(
        discord_user_id=interaction.user.id,
        guild_id=interaction.guild_id,
    )
    embed = _finch_embed(
        interaction,
        title="Registration Removed" if removed else "No Registration Found",
        description=(
            "Your Discord account is no longer linked to a FoundryDock player."
            if removed
            else "You were not registered with Finch on this server."
        ),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(name="me", description="Show your private FoundryDock raid brief.")
async def me(interaction: discord.Interaction) -> None:
    assert bot is not None
    registration = _registration_for(interaction)
    if registration is None:
        embed = _finch_embed(
            interaction,
            title="🐦‍⬛  Finch Needs Your Name",
            description=(
                "You are not registered on this server yet.\n"
                "Use **/register** with your FoundryDock Team and Personnel player name."
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    schedule = bot.foundry.team_schedule_text(registration.team_name)
    plan = bot.foundry.active_plan_for_team(registration.team_name)

    embed = _finch_embed(
        interaction,
        title=f"🐦‍⬛  {registration.player_name}",
        description=f"**{registration.team_name}**",
        color=FINCH_TEAL,
    )
    embed.add_field(name="🕘 Schedule", value=_trim(schedule), inline=False)

    if plan is None:
        embed.add_field(
            name="Raid Plan",
            value="No single active Raid Plan is currently set for this team.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed.add_field(name="🗺️ Raid Plan", value=plan.name, inline=False)

    try:
        brief = bot.foundry.build_brief(
            plan_ref=plan.plan_id,
            player_ref=registration.player_name,
        )
    except LookupError:
        embed.add_field(
            name="Your Seat",
            value="You are not seated in the active Raid Plan yet.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    seat = " · ".join(
        part for part in (brief.seat_id, brief.role, brief.eso_class) if part
    )
    if seat:
        embed.add_field(name="🎟️ Seat", value=seat, inline=False)
    if brief.build:
        embed.add_field(name="⚒️ Build", value=_trim(brief.build), inline=False)
    if brief.gear_sets:
        embed.add_field(
            name="🛡️ Gear",
            value=_trim("\n".join(f"• {item}" for item in brief.gear_sets)),
            inline=False,
        )
    if brief.assignments:
        embed.add_field(
            name="📌 Assignments",
            value=_trim("\n".join(f"• {item}" for item in brief.assignments)),
            inline=False,
        )
    embed.set_footer(text="Use /build for complete private build details · Finch")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(
    name="build",
    description="Show your private planned FoundryDock build.",
)
@app_commands.describe(
    player="Optional player override. Leave blank to use your Finch registration.",
    plan="Optional Raid Plan name/id. Leave blank to use your registered Team's active plan.",
)
async def build(
    interaction: discord.Interaction,
    player: str = "",
    plan: str = "",
) -> None:
    assert bot is not None
    registration = _registration_for(interaction)
    player_ref = player.strip()
    plan_ref = plan.strip()

    if not player_ref and registration is not None:
        player_ref = registration.player_name
    if not plan_ref and registration is not None:
        plan_ref = _registered_plan_ref(registration.team_name)

    if not player_ref:
        embed = _finch_embed(
            interaction,
            title="Registration Required",
            description=(
                "Use **/register** once and Finch will remember which FoundryDock "
                "player you are on this server."
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        brief = bot.foundry.build_brief(
            plan_ref=plan_ref,
            player_ref=player_ref,
        )
    except LookupError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    await interaction.response.send_message(
        embed=_build_embed(interaction, brief),
        ephemeral=True,
    )


@app_commands.command(name="raid", description="Show a saved FoundryDock Raid Plan.")
@app_commands.describe(
    plan="Saved Raid Plan name or stable id. Leave blank when only one plan is active."
)
async def raid(interaction: discord.Interaction, plan: str = "") -> None:
    assert bot is not None
    try:
        brief = bot.foundry.raid_brief(plan)
    except LookupError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return
    await _respond(interaction, format_raid_brief(brief), ephemeral=True)


@app_commands.command(
    name="schedule",
    description="Show your FoundryDock Team raid schedule.",
)
@app_commands.describe(
    team="Optional Team name. Leave blank to use your Finch registration."
)
async def schedule(interaction: discord.Interaction, team: str = "") -> None:
    assert bot is not None
    registration = _registration_for(interaction)
    team_name = team.strip() or (
        registration.team_name if registration is not None else ""
    )
    if not team_name:
        await interaction.response.send_message(
            "Register with Finch first using /register, or provide a Team name.",
            ephemeral=True,
        )
        return

    schedule_text = bot.foundry.team_schedule_text(team_name)
    embed = _finch_embed(
        interaction,
        title="🕘  Raid Schedule",
        description=f"**{team_name}**",
        color=FINCH_GOLD,
    )
    embed.add_field(name="When", value=_trim(schedule_text), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(
    name="strat",
    description="Show reviewed FoundryDock strategy notes for an encounter.",
)
@app_commands.describe(
    encounter="Canonical encounter id used by FoundryDock.",
    name="Optional display name when the encounter evidence does not supply one.",
)
async def strat(
    interaction: discord.Interaction,
    encounter: str,
    name: str = "",
) -> None:
    assert bot is not None
    brief = bot.foundry.strategy_brief(
        encounter_id=encounter,
        encounter_name=name,
    )
    await _respond(
        interaction,
        format_strategy_brief(brief),
        ephemeral=True,
    )


@app_commands.command(name="map", description="Show a saved FoundryDock raid map.")
@app_commands.describe(
    encounter="Canonical encounter id used by FoundryDock.",
    map_id="Optional map id. Leave blank when only one saved map is needed.",
)
async def raid_map(
    interaction: discord.Interaction,
    encounter: str,
    map_id: str = "",
) -> None:
    assert bot is not None
    try:
        maps = bot.foundry.raid_maps(encounter)
    except ValueError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    if map_id:
        wanted = map_id.strip().casefold()
        maps = tuple(row for row in maps if row.map_id.casefold() == wanted)

    if not maps:
        await interaction.response.send_message(
            "No saved FoundryDock raid map matches that encounter.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)
    for row in maps[:4]:
        if not row.path.is_file():
            continue
        embed = _finch_embed(
            interaction,
            title=f"🗺️  {row.label}",
            description=row.encounter_id,
            color=FINCH_GOLD,
        )
        file = discord.File(row.path, filename=row.path.name)
        embed.set_image(url=f"attachment://{row.path.name}")
        await interaction.followup.send(
            embed=embed,
            file=file,
            ephemeral=True,
        )


@app_commands.command(
    name="finch",
    description="Show Finch's FoundryDock companion capabilities.",
)
async def finch(interaction: discord.Interaction) -> None:
    embed = _finch_embed(
        interaction,
        title="🐦‍⬛  Finch",
        description=(
            "**FoundryDock Raid Companion**\n"
            "Private raid information, without making everyone excavate Discord."
        ),
        color=FINCH_PURPLE,
    )
    embed.add_field(
        name="Your Raid",
        value=(
            "**/register**  Link your Discord identity\n"
            "**/me**  Your current raid brief\n"
            "**/build**  Your complete planned build\n"
            "**/schedule**  Your Team schedule"
        ),
        inline=False,
    )
    embed.add_field(
        name="Field Notes",
        value=(
            "**/strat**  Reviewed encounter strategy\n"
            "**/map**  Saved raid maps"
        ),
        inline=False,
    )
    embed.add_field(
        name="Raid Lead",
        value="**/raid**  Full saved Raid Plan",
        inline=False,
    )
    embed.set_footer(
        text="FoundryDock keeps the truth. Finch carries the notes."
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


def create_bot(config: DiscordCompanionConfig | None = None) -> FinchBot:
    global bot
    config = config or load_config()
    instance = FinchBot(config)
    for command in (
        register,
        unregister,
        me,
        raid,
        build,
        strat,
        raid_map,
        schedule,
        finch,
    ):
        instance.tree.add_command(command)
    bot = instance
    return instance


def main() -> None:
    config_path = write_example_config()
    config = load_config(config_path)
    token = load_bot_token(config)
    if not token:
        raise RuntimeError(
            "Discord token is missing. Run the Finch token setup once; "
            "the token is stored in the operating-system credential vault."
        )
    create_bot(config).run(token, log_handler=None)


if __name__ == "__main__":
    main()
