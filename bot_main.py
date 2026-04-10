import traceback
from pathlib import Path

import discord
from discord.ext import commands

from core.help import CustomHelpCommand
from core.logger import get_logger

logger = get_logger(__name__)

COGS_DIR = Path(__file__).parent / "cogs"


class MusicBot(commands.Bot):
    """Custom Bot subclass with dynamic Cog loading and global error handling."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.help_command = CustomHelpCommand()

    # ── Lifecycle ────────────────────────────────────────────────

    async def setup_hook(self) -> None:
        """Dynamically discover and load every Cog in the cogs/ directory."""
        for cog_file in sorted(COGS_DIR.glob("*.py")):
            if cog_file.name.startswith("_"):
                continue
            extension = f"cogs.{cog_file.stem}"
            try:
                await self.load_extension(extension)
                logger.info("Loaded extension: %s", extension)
            except Exception as exc:
                logger.error("Failed to load extension %s: %s", extension, exc)

    async def on_ready(self) -> None:
        logger.info("Bot is online as %s (ID: %s)", self.user, self.user.id)

    # ── Global error handler ────────────────────────────────────

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handles command errors gracefully with user-facing embeds."""
        embed = discord.Embed(color=discord.Color.red())

        if isinstance(error, commands.CommandNotFound):
            embed.title = "Unknown Command"
            embed.description = f"`{ctx.invoked_with}` is not a valid command."
        elif isinstance(error, commands.MissingRequiredArgument):
            embed.title = "Missing Argument"
            embed.description = f"**`{error.param.name}`** is required.\nUsage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
        elif isinstance(error, commands.CommandInvokeError):
            embed.title = "Command Error"
            embed.description = "Something went wrong while running that command."
            logger.error(
                "CommandInvokeError in %s:\n%s",
                ctx.command,
                "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            )
        else:
            embed.title = "Error"
            embed.description = str(error)
            logger.warning("Unhandled command error: %s", error)

        await ctx.send(embed=embed)
