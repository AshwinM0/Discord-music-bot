from discord.ext import commands
from discord.utils import get
from core.database import GuildConfig
from core.resource import resources

def dj_required():
    """A decorator that ensures the user has the configured DJ role, or is an admin."""
    async def predicate(ctx: commands.Context):
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return True

        config = await GuildConfig.get_or_none(guild_id=ctx.guild.id)
        if not config or not config.dj_role_id:
            return True  # No role configured, allow anyone
        
        dj_role_id = config.dj_role_id

        if get(ctx.author.roles, id=dj_role_id):
            return True

        # Failed check
        role = ctx.guild.get_role(dj_role_id)
        role_name = role.name if role else f"deleted-role-{dj_role_id}"
        raise commands.CheckFailure(resources.get("admin.not_dj_role", role=role_name))

    return commands.check(predicate)
