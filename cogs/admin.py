import discord
from discord import app_commands
from discord.ext import commands
from core.database import GuildConfig
from core.resource import resources
from core.logger import get_logger

logger = get_logger(__name__)

class Admin(commands.Cog):
    """Server administration commands for configuring the bot."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Ensure only administrators can run these commands."""
        if not ctx.guild:
            return False
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                description=resources.get("admin.not_admin"),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return False
        return True

    @commands.hybrid_command()
    @app_commands.describe(channel="The text channel to lock music commands to. Omit to unlock.")
    async def setchannel(self, ctx: commands.Context, channel: discord.TextChannel = None) -> None:
        """Lock music commands to a specific text channel. Omit the channel to unlock."""
        channel_id = channel.id if channel else None

        config, _ = await GuildConfig.get_or_create(guild_id=ctx.guild.id)
        config.music_channel_id = channel_id
        await config.save()

        if channel:
            embed = discord.Embed(
                description=resources.get("admin.channel_set", channel=channel.mention),
                color=discord.Color.green()
            )
            logger.info("Guild %s locked to channel %s", ctx.guild.id, channel_id)
        else:
            embed = discord.Embed(
                description=resources.get("admin.channel_cleared"),
                color=discord.Color.green()
            )
            logger.info("Guild %s unlocked channel restrictions", ctx.guild.id)

        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @app_commands.describe(role="The role required for DJ commands. Omit to unlock.")
    async def setdj(self, ctx: commands.Context, role: discord.Role = None) -> None:
        """Set a DJ role that is required for destructive commands. Omit the role to unlock."""
        role_id = role.id if role else None

        config, _ = await GuildConfig.get_or_create(guild_id=ctx.guild.id)
        config.dj_role_id = role_id
        await config.save()

        if role:
            embed = discord.Embed(
                description=resources.get("admin.dj_set", role=role.mention),
                color=discord.Color.green()
            )
            logger.info("Guild %s set DJ role to %s", ctx.guild.id, role_id)
        else:
            embed = discord.Embed(
                description=resources.get("admin.dj_cleared"),
                color=discord.Color.green()
            )
            logger.info("Guild %s removed DJ role", ctx.guild.id)

        await ctx.send(embed=embed)

    # ── Owner-only sync command ──────────────────────────────────
    # This stays as a plain prefix command so it always works,
    # even before any slash commands are synced.

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, spec: str | None = None) -> None:
        """
        Sync slash commands to Discord. Owner only.
        Usage:
          <>sync        -> Sync to the current guild (instant).
          <>sync global -> Sync globally (up to 1 hour).
          <>sync clear  -> Clear guild-specific commands.
        """
        if spec == "global":
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Synced **{len(synced)}** commands globally.")
            logger.info("Global slash command sync: %d commands", len(synced))
        elif spec == "clear":
            self.bot.tree.clear_commands(guild=ctx.guild)
            await self.bot.tree.sync(guild=ctx.guild)
            await ctx.send("🗑️ Cleared slash commands for this guild.")
            logger.info("Cleared guild slash commands for %s", ctx.guild.id)
        else:
            self.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await self.bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"✅ Synced **{len(synced)}** commands to this guild.")
            logger.info("Guild slash command sync for %s: %d commands", ctx.guild.id, len(synced))

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
