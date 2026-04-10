import discord
from discord.ext import commands

class CustomHelpCommand(commands.HelpCommand):
    """Custom visually-pleasing Help Command using embeds."""

    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title="Bot Commands Overview",
            description="Here's a list of all available commands. Type `<>help <command>` for more details.",
            color=discord.Color.blurple()
        )
        for cog, commands_list in mapping.items():
            filtered = await self.filter_commands(commands_list, sort=True)
            if not filtered:
                continue
            name = getattr(cog, "qualified_name", "General")
            signatures = [f"`{self.context.clean_prefix}{c.name}` - {c.short_doc or 'No description'}" for c in filtered]
            embed.add_field(name=f"📖 {name}", value="\n".join(signatures), inline=False)
        
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=f"Command: {self.context.clean_prefix}{command.qualified_name}",
            description=command.help or "No description provided.",
            color=discord.Color.blurple()
        )
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(command.aliases), inline=False)
            
        embed.add_field(name="Usage", value=f"`{self.context.clean_prefix}{command.qualified_name} {command.signature}`", inline=False)
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=f"Category: {cog.qualified_name}",
            description=cog.description or "No description available.",
            color=discord.Color.blurple()
        )
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        signatures = [f"`{self.context.clean_prefix}{c.name}` - {c.short_doc or 'No description'}" for c in filtered]
        if signatures:
            embed.add_field(name="Commands", value="\n".join(signatures), inline=False)
        await self.get_destination().send(embed=embed)
