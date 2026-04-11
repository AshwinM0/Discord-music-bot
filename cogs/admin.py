import discord
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

    @commands.command()
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

    @commands.command()
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

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
