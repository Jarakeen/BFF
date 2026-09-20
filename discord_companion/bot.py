from __future__ import annotations

"""Finch Discord bot entry point."""

import discord
from discord import app_commands
from discord.ext import commands, tasks

from discord_companion.changes import BuildChangeMonitor
from discord_companion.config import DiscordCompanionConfig, load_config, write_example_config
from discord_companion.credentials import load_bot_token
from discord_companion.formatting import (
    format_build_brief,
    format_raid_brief,
    format_strategy_brief,
    split_discord_message,
)
from discord_companion.reminders import RaidReminderService
from engine.config import get_data_dir
from services.discord_companion_service import FoundryDockDiscordCompanionService
from services.eso_database import EsoDatabase
from services.raid_plan_repository import RaidPlanRepository
from services.roster_service import RosterService


def _companion() -> FoundryDockDiscordCompanionService:
    data_dir = get_data_dir()
    database = EsoDatabase(data_dir / "eso.db")
    roster = RosterService(database)
    return FoundryDockDiscordCompanionService(
        plan_repository=RaidPlanRepository(data_dir / "raid_plans.json"),
        roster_service=roster,
        data_dir=data_dir,
    )


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
                allowed_mentions=discord.AllowedMentions(roles=True, users=False, everyone=False),
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


async def _respond(interaction: discord.Interaction, text: str, *, ephemeral: bool = False) -> None:
    chunks = split_discord_message(text)
    await interaction.response.send_message(chunks[0], ephemeral=ephemeral)
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk, ephemeral=ephemeral)


@app_commands.command(name="raid", description="Show a saved FoundryDock Raid Plan.")
@app_commands.describe(plan="Saved Raid Plan name or stable id. Leave blank when only one plan is active.")
async def raid(interaction: discord.Interaction, plan: str = "") -> None:
    assert bot is not None
    try:
        brief = bot.foundry.raid_brief(plan)
    except LookupError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return
    await _respond(interaction, format_raid_brief(brief))


@app_commands.command(name="build", description="Show a player's planned FoundryDock build for a Raid Plan.")
@app_commands.describe(
    player="Gamertag, Discord name saved in Personnel, or seat id.",
    plan="Saved Raid Plan name or stable id. Leave blank when only one plan is active.",
)
async def build(interaction: discord.Interaction, player: str, plan: str = "") -> None:
    assert bot is not None
    try:
        brief = bot.foundry.build_brief(plan_ref=plan, player_ref=player)
    except LookupError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return
    await _respond(interaction, format_build_brief(brief), ephemeral=True)


@app_commands.command(name="strat", description="Show reviewed FoundryDock strategy notes for an encounter.")
@app_commands.describe(
    encounter="Canonical encounter id used by FoundryDock.",
    name="Optional display name when the encounter evidence does not supply one.",
)
async def strat(interaction: discord.Interaction, encounter: str, name: str = "") -> None:
    assert bot is not None
    brief = bot.foundry.strategy_brief(encounter_id=encounter, encounter_name=name)
    await _respond(interaction, format_strategy_brief(brief))


@app_commands.command(name="map", description="Post a saved FoundryDock raid map for an encounter.")
@app_commands.describe(
    encounter="Canonical encounter id used by FoundryDock.",
    map_id="Optional map id. Leave blank when only one saved map is needed.",
)
async def raid_map(interaction: discord.Interaction, encounter: str, map_id: str = "") -> None:
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

    await interaction.response.defer()
    for row in maps[:4]:
        if not row.path.is_file():
            continue
        await interaction.followup.send(
            content=f"**{row.label}** · {row.encounter_id}",
            file=discord.File(row.path),
        )


@app_commands.command(name="schedule", description="Show a FoundryDock Team raid schedule.")
@app_commands.describe(team="FoundryDock Team name.")
async def schedule(interaction: discord.Interaction, team: str) -> None:
    assert bot is not None
    text = bot.foundry.team_schedule_text(team)
    await interaction.response.send_message(f"**{team}** · {text}")


@app_commands.command(name="finch", description="Show Finch's FoundryDock companion capabilities.")
async def finch(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        "**Finch · FoundryDock Raid Companion**\n"
        "/raid — saved Raid Plan\n"
        "/build — your planned build and assignments\n"
        "/strat — reviewed encounter strategy\n"
        "/map — saved raid maps\n"
        "/schedule — team schedule\n"
        "Raid reminders use the schedule already saved in FoundryDock."
    )


def create_bot(config: DiscordCompanionConfig | None = None) -> FinchBot:
    global bot
    config = config or load_config()
    instance = FinchBot(config)
    for command in (raid, build, strat, raid_map, schedule, finch):
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
