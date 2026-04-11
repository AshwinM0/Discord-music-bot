import traceback
from pathlib import Path

import discord
from discord.ext import commands

from core.help import CustomHelpCommand
from core.logger import get_logger
from core.resource import resources
from core.database import init_db, close_db

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
        await init_db()
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

    async def close(self) -> None:
        """Close database connection and shutdown bot."""
        await close_db()
        await super().close()

    # ── Global error handler ────────────────────────────────────

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handles command errors gracefully with user-facing embeds."""
        embed = discord.Embed(color=discord.Color.red())

        if isinstance(error, commands.CommandNotFound):
            embed.title = resources.get("errors.unknown_comm_title")
            embed.description = resources.get("errors.unknown_comm_desc", command=ctx.invoked_with)
        elif isinstance(error, commands.CommandOnCooldown):
            embed.title = resources.get("errors.cooldown_title")
            embed.description = resources.get("errors.cooldown_desc", retry=f"{error.retry_after:.1f}")
            embed.color = discord.Color.orange()
        elif isinstance(error, commands.MissingRequiredArgument):
            embed.title = resources.get("errors.missing_arg_title")
            embed.description = resources.get("errors.missing_arg_desc", param=error.param.name, prefix=ctx.prefix, command=ctx.command.qualified_name, signature=ctx.command.signature)
        elif isinstance(error, commands.CommandInvokeError):
            embed.title = resources.get("errors.invoke_err_title")
            embed.description = resources.get("errors.invoke_err_desc")
            logger.error(
                "CommandInvokeError in %s:\n%s",
                ctx.command,
                "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            )
        elif isinstance(error, commands.CheckFailure):
            embed.title = "Permission Denied"
            embed.description = str(error)
        else:
            embed.title = resources.get("errors.general_err_title")
            embed.description = resources.get("errors.general_err_desc", error=str(error))
            logger.warning("Unhandled command error: %s", error)

        await ctx.send(embed=embed)
