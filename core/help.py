import discord
from discord.ext import commands
from core.resource import resources

class CustomHelpCommand(commands.HelpCommand):
    """Custom visually-pleasing Help Command using embeds."""

    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title=resources.get("help.overview_title"),
            description=resources.get("help.overview_desc"),
            color=discord.Color.blurple()
        )
        for cog, commands_list in mapping.items():
            filtered = await self.filter_commands(commands_list, sort=True)
            if not filtered:
                continue
            name = getattr(cog, "qualified_name", "General")
            signatures = [resources.get("help.command_signature", prefix=self.context.clean_prefix, name=c.name, doc=c.short_doc or 'No description') for c in filtered]
            embed.add_field(name=resources.get("help.category_field", name=name), value="\n".join(signatures), inline=False)
        
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=resources.get("help.command_title", prefix=self.context.clean_prefix, name=command.qualified_name),
            description=command.help or "No description provided.",
            color=discord.Color.blurple()
        )
        if command.aliases:
            embed.add_field(name=resources.get("help.aliases_field"), value=", ".join(command.aliases), inline=False)
            
        embed.add_field(name=resources.get("help.usage_field"), value=resources.get("help.usage_value", prefix=self.context.clean_prefix, name=command.qualified_name, signature=command.signature), inline=False)
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=resources.get("help.cog_title", name=cog.qualified_name),
            description=cog.description or "No description available.",
            color=discord.Color.blurple()
        )
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        signatures = [resources.get("help.command_signature", prefix=self.context.clean_prefix, name=c.name, doc=c.short_doc or 'No description') for c in filtered]
        if signatures:
            embed.add_field(name="Commands", value="\n".join(signatures), inline=False)
        await self.get_destination().send(embed=embed)
